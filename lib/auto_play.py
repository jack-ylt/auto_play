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
# from lib import role

# from ui_data import SCREEN_DICT
# from player import Player, FindTimeout


TASK_DICT = {
    'daily_play': [
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
    ],
    'shen_yuan_mo_ku': ['ShenYuanMoKu', ],
}


async def play(goal, player, role, g_queue):
    player.logger.info(f"start to play, role: {role}")

    await role.load_all_attributes()
    game_obj = Gamer(player, role)

    try:
        await game_obj.login()
        await g_queue.put(('running', player.window, role))
    except FindTimeout:
        await g_queue.put(('error', player.window, role))
        return

    counter = PlayCounter(role.game + '_' + role.user)
    task_list = TASK_DICT[goal]

    error_count = 0
    restart_count = 0
    failed_set = set()
    for cls_name in task_list:
        try:
            await game_obj.goto_main_ui()
        except FindTimeout as e:
            msg = "go to main interface failed"
            player.logger.error(msg + '\n' + str(e))
            player.save_operation_pics(msg)

            # 会不到主界面，可能卡住了，需要重启
            error_count += 1
            if restart_count < 2:
                restart_count += 1
                await game_obj.restart()
            else:
                break

        player.logger.info("Start to run: " + cls_name)
        obj = getattr(tasks, cls_name)(player, role.play_setting, counter)
        try:
            await obj.run()
            error_count = max(error_count - 1, 0)
        except FindTimeout as e:
            player.logger.error(str(e))
            player.save_operation_pics(str(e))

            if cls_name not in failed_set:
                failed_set.add(cls_name)
                task_list.append(cls_name)

            error_count += 1
            # 连续两次任务失败，可能游戏出错了，需要重启
            if error_count >= 3:
                if restart_count < 2:
                    restart_count += 1
                    await game_obj.restart()
                else:
                    break

        finally:
            counter.save_data()

    player.logger.info(f"play for {role} done")
    await g_queue.put(('done', player.window, role))
