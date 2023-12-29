##############################################################################
# 游戏主控，负责一个游戏窗口的所有任务
#
##############################################################################

# import asyncio
# import logging
# from lib import tasks
import tasks
from lib.gamer import Gamer
from lib.player import FindTimeout
from lib.recorder import PlayCounter
from lib.role import Role
import time
import datetime
# from lib import role

# from ui_data import SCREEN_DICT
# from player import Player, FindTimeout

from lib.global_vals import GameNotFound, UnsupportGame, LoginTimeout, RestartTooMany, UserConfigError, NotInGameMain, MouseFailure


shen_yuan_tasks = ('ShenYuanMoKu', )

daily_play_tasks = (
    'KuaiJieZhiNan',
    'ZhouNianQing5',
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
    'JiYiDangAnGuan',
    'YiJiMoKu',
    'YingXiongYuanZheng',
    'MiGong',
    'LianSaiBaoXiang',
    'GongHuiZhan',
    'GaoTaShiLian',
    'JueDiQiuSheng',
    'ShiJieBoss',
    'XinChunQingDian',
    'KuaiJieZhiNan',
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
            await g_queue.put(('config error', player.window, role))
        except GameNotFound:
            await g_queue.put(('game not found', player.window, role))
            player.save_operation_pics('game not found')
        except LoginTimeout:
            await g_queue.put(('login timeout', player.window, role))
        except RestartTooMany:
            await g_queue.put(('restart to many times', player.window, role))
        except MouseFailure:
            await g_queue.put(('mouse failure', player.window, role))
            player.save_operation_pics('mouse failure')
        except Exception:
            player.logger.exception("unexpected error")
            player.save_operation_pics('unexpected error')
            await g_queue.put(('unexpected error', player.window, role))
        else:
            await g_queue.put(('done', player.window, role))
        finally:
            end_t = time.time()
            cost_second = int(end_t - start_t)
            player.logger.info(
                f'Run {goal} for {role} on {player.window} end. Cost {cost_second}s.')

    elif goal == 'quick_play':
        start_t = time.time()
        player.logger.info(f'Run {goal} on {player.window} start')
        gamer = Gamer(player)
        have_error = False

        role = Role()
        try:
            await role.load_all_attributes()
        except Exception as err:
            player.logger.error(str(err))
            raise UserConfigError()

        failed_set = set()
        error_count = 0
        task_list = list(daily_play_tasks)

        for cls_name in task_list:
            player.logger.info("Start to run: " + cls_name)
            obj = getattr(tasks, cls_name)(player, role.play_setting, None)

            try:
                await obj.run()
                error_count = max(error_count - 1, 0)
            except FindTimeout as err:
                error_count += 1
                player.logger.error(f"run {cls_name} faled: {str(err)}")
                player.save_operation_pics(str(err))

                # 失败了，就过段时间再尝试一次, 还失败，就算了
                if cls_name not in failed_set:
                    failed_set.add(cls_name)
                    task_list.append(cls_name)

                # 连续两次任务失败，可能游戏出错了
                if error_count >= 2:
                    break

            try:
                await gamer.goto_main_ui()
            except FindTimeout as err:
                error_count += 1
                msg = "go to main interface failed"
                player.logger.error(msg + '\n' + str(err))
                player.save_operation_pics(msg)

                # 回不到主界面，可能卡住了
                break

        end_t = time.time()
        cost_second = int(end_t - start_t)
        player.logger.info(
            f'Run {goal} on {player.window} end. Cost {cost_second}s.')
            
        if have_error:
            await g_queue.put(('unexpected error', player.window, role))
        else:
            await g_queue.put(('done', player.window, role))


    elif goal == 'shen_yuan_mo_ku':
        start_t = time.time()
        player.logger.info(f'Run {goal} on {player.window} start')
        gamer = Gamer(player)

        cls_name = 'ShenYuanMoKu'
        try:
            await gamer.goto_main_ui()
            player.logger.info("Start to run: " + cls_name)
            obj = getattr(tasks, cls_name)(player, None, None)
            await obj.run()
        except Exception:
            player.logger.exception("unexpected error")
            player.save_operation_pics('unexpected error')
            await g_queue.put(('unexpected error', player.window, role))
        else:
            await g_queue.put(('done', player.window, role))
        finally:

            end_t = time.time()
            cost_second = int(end_t - start_t)
            player.logger.info(
                f'Run {goal} on {player.window} end. Cost {cost_second}s.')


async def daily_play(player, role):
    try:
        await role.load_all_attributes()
    except Exception as err:
        player.logger.error(str(err))
        raise UserConfigError()

    gamer = Gamer(player)

    try:
        await gamer.login(role)
    except FindTimeout:
        msg = 'login Timeout.'
        player.logger.warning(msg)
        player.save_operation_pics(msg)
        # await game_obj.close_game()
        raise LoginTimeout()

    counter = PlayCounter(role.game + '_' + role.user)
    counter.set_global('run_count', counter.get_global('run_count') + 1)
    counter.set_global('start_time', time.time())

    task_list = list(daily_play_tasks)

    error_count = 0
    failed_set = set()
    auto = AutoRecover(gamer)

    for cls_name in task_list:
        player.logger.info("------------------- Start to run: " + cls_name + " -------------------")
        obj = getattr(tasks, cls_name)(player, role.play_setting, counter)
        try:
            if obj.test():
                await obj.run()
                error_count = max(error_count - 1, 0)
                player.logger.info("End to run: " + cls_name)
            else:
                player.logger.info("Skip to run: " + cls_name)
        except FindTimeout as err:
            error_count += 1
            player.logger.error(f"run {cls_name} faled: {str(err)}")
            player.save_operation_pics(str(err))

            # 失败了，就过段时间再尝试一次, 还失败，就算了
            if cls_name not in failed_set:
                failed_set.add(cls_name)
                task_list.append(cls_name)

            # 连续两次任务失败，可能游戏出错了，需要重启
            if error_count >= 2:
                try:
                    await auto.recover(role)
                except FindTimeout:
                    raise LoginTimeout()
        # except MouseFailure as err:
        #     # 鼠标失灵，试试重启客户端
        #     # -> 没用，移动鼠标都办不到，根本没法重启
        #     player.logger.error(f"run {cls_name} faled: {str(err)}")
        #     player.save_operation_pics(str(err))
        #     try:
        #         await auto.recover(role)
        #     except FindTimeout:
        #         raise LoginTimeout()
        finally:
            counter.save_data()

        try:
            await gamer.goto_main_ui()
        except FindTimeout as err:
            error_count += 1
            msg = "go to main interface failed"
            player.logger.error(msg + '\n' + str(err))
            player.save_operation_pics(msg)

            # 回不到主界面，可能卡住了，需要重启
            await auto.recover(role)

    # if done all success, save done time
    counter.set_global('done_time', time.time())
    counter.save_data()


class AutoRecover():
    """通过重启，恢复程序的运行"""

    def __init__(self, gamer):
        self.gamer = gamer
        self.restart_count = 0

    async def recover(self, role):
        if self.restart_count < 2:
            self.restart_count += 1
            await self.gamer.restart(role)
            # try:
            #     await self.gamer.restart(role)
            # except FindTimeout:
            #     raise MouseFailure()
        else:
            raise RestartTooMany()
