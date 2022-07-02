##############################################################################
# 游戏主控，负责一个游戏窗口的所有任务
#
##############################################################################

# import asyncio
# import logging
from lib import tasks
from lib.gamer import Gamer
from lib.player import FindTimeout
from lib.recorder import PlayCounter
from lib.role import Role
import time
# from lib import role

# from ui_data import SCREEN_DICT
# from player import Player, FindTimeout

from lib.global_vals import GameNotFound, UnsupportGame, LoginTimeout, RestartTooMany, UserConfigError


shen_yuan_tasks = ('ShenYuanMoKu', )

daily_play_tasks = (
    'MeiRiRenWu',
    'XianShiJie',
    'YouJian',
    'HaoYou',
    'SheQvZhuLi',
    'TiaoZhanFuben',
    'GongHui',
    'MeiRiQianDao',
    'JueDiKongJian',
    'ShengCunJiaYuan',
    'YaoQingYingXion',
    'WuQiKu',
    'XingCunJiangLi',
    'ShiChang',
    'JingJiChang',
    'GuanJunShiLian',
    'YongZheFuBen',
    'XingYunZhuanPan',
    'RenWuLan',
    'VipShangDian',
    'YingXiongYuanZheng',
    'MiGong',
    'RenWu',
)


async def play(goal, player, role, g_queue):
    if goal == 'daily_play':
        func = daily_play
        args = (player, role)

    start_t = time.time()
    player.logger.info(f'Run {goal} for {role} on {player.window} start')

    try:
        await func(*args)
    except UserConfigError:
        g_queue.put(('config error', player.window, role))
    except GameNotFound:
        g_queue.put(('game not found', player.window, role))
    except LoginTimeout:
        g_queue.put(('login timeout', player.window, role))
    except RestartTooMany:
        g_queue.put(('restart to many times', player.window, role))
    except FindTimeout:
        g_queue.put(('unknow error happend', player.window, role))
    else:
        await g_queue.put(('done', player.window, role))
    finally:
        end_t = time.time()
        cost_second = int(end_t - start_t)
        player.logger.info(
            f'Run {goal} for {role} on {player.window} end. Cost {cost_second}s。')


async def daily_play(player, role):
    try:
        await role.load_all_attributes()
    except Exception as err:
        player.logger.eror(str(err))
        raise UserConfigError

    gamer = Gamer(player, role)

    try:
        await gamer.login()
    except FindTimeout:
        msg = 'login Timeout.'
        player.logger.warning(msg)
        player.save_operation_pics(msg)
        # await game_obj.close_game()
        raise LoginTimeout

    counter = PlayCounter(role.game + '_' + role.user)
    task_list = list(daily_play_tasks)

    error_count = 0
    failed_set = set()
    auto = AutoRecover(gamer)

    for cls_name in task_list:
        player.logger.info("Start to run: " + cls_name)
        obj = getattr(tasks, cls_name)(player, role.play_setting, counter)
        try:
            await obj.run()
            error_count = max(error_count - 1, 0)
        except FindTimeout as e:
            error_count += 1
            player.logger.error(str(e))
            player.save_operation_pics(str(e))

            # 失败了，就过段时间再尝试一次, 还失败，就算了
            if cls_name not in failed_set:
                failed_set.add(cls_name)
                task_list.append(cls_name)

            # 连续两次任务失败，可能游戏出错了，需要重启
            if error_count >= 2:
                await auto.recover()
        finally:
            counter.save_data()

        try:
            await gamer.goto_main_ui()
        except FindTimeout as e:
            error_count += 1
            msg = "go to main interface failed"
            player.logger.error(msg + '\n' + str(e))
            player.save_operation_pics(msg)

            # 回不到主界面，可能卡住了，需要重启
            await auto.recover()


async def shen_yuan_mo_ku(player):
    pass


class AutoRecover():
    """通过重启，恢复程序的运行"""

    def __init__(self, gamer):
        self.gamer = gamer
        self.restart_count = 0

    async def recover(self):
        if self.restart_count < 2:
            self.restart_count += 1
            await self.gamer.restart()
        else:
            raise RestartTooMany
