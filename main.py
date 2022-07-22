# -*-coding:utf-8-*-

"""
模拟玩家，自动玩游戏，打怪升级、做任务。
最多支持同时模拟3位玩家
"""


import asyncio
import os
import signal
import sys
from multiprocessing import freeze_support
from playsound import playsound
import time
import keyboard
from collections import defaultdict

from lib import emulator
from lib.auto_play import play
from lib.global_vals import EmulatorNotFound, EmulatorSetError, UserConfigError
from lib.helper import main_dir
from lib.mylogs import make_logger, clean_old_logs
from lib.player import Player
from lib.read_cfg import read_game_user
from lib.role import Role, Roles
from lib.windows import Window
from lib.recorder import PlayCounter
from collections import defaultdict

os.chdir(main_dir)
sys.path.insert(0, main_dir)

logger = make_logger('full')


class UserStop(Exception):
    """
    when user press blank button, raise 
    """
    pass


def handler(signum, frame):
    logger.info('SIGINT for PID=' + str(os.getpid()))


def init():
    signal.signal(signal.SIGINT, handler)


async def main(goal):
    start_t = time.time()
    g_lock = asyncio.Lock()
    g_sem = asyncio.Semaphore(1)
    g_queue = asyncio.Queue()

    try:
        roles = Roles()
    except UserConfigError as e:
        return stop_play(str(e))


    logger.info("clean old logs")
    clean_old_logs()

    player = Player(g_lock=g_lock, window=Window('full'), logger=logger)
    emu = emulator.Emulator(player)

    if goal == 'daily_play':
        try:
            async for window in emu.start_all_emulator():
                a_role = roles.get_idle_role()
                if a_role:
                    create_play_task(a_role, g_lock, g_sem, window, g_queue)
                else:
                    break
        except EmulatorNotFound:
            return stop_play("未找到夜神模拟器，请先安装夜神模拟器")
        except EmulatorSetError as e:
            logger.error(str(e))
            return stop_play("启动模拟器异常，请稍后重试。")

        failed_rols = defaultdict(int)
        while True:
            status, window, role = await g_queue.get()

            if status == 'done':
                logger.info(f'{role} done on {window.name}')
                roles.set_role_status(role, 'done')

                if roles.is_all_roles_done():
                    playsound('./sounds/end.mp3')
                    end_t = time.time()
                    cost_minute = int((end_t - start_t) / 60)
                    logger.info(f'Done, 为您节省时间约{cost_minute}分钟。')
                    break

                # a_role = roles.get_idle_role(game=role.game) or roles.get_idle_role()
                a_role = roles.get_idle_role()
                if a_role:
                    create_play_task(a_role, g_lock, g_sem, window, g_queue)
            elif status == 'config error':
                return stop_play(f"配置错误，请先修正配置")
            elif status == 'mouse failure':
                return stop_play(f"糟糕，鼠标貌似失灵了，请稍后重试")
            elif status == 'unexpected error':
                return stop_play(f"未知错误，请稍后重试")
            elif status == 'game not found':
                return stop_play(f"未找到{role.game}，请在每个模拟器窗口都安装好游戏")
            else:
                # 比如验证码出来了，所以就换个账号登陆
                logger.warning(f'{role} run error on {window.name}')
                a_role = roles.get_idle_role()
                if a_role:
                    create_play_task(a_role, g_lock, g_sem, window, g_queue)

                # 失败太多次，就不必重试了（可能是用户改密码了，系统维护……）
                failed_rols[str(role)] += 1
                if failed_rols[str(role)] < 3:
                    roles.set_role_status(role, 'idle')
                else:
                    roles.set_role_status(role, 'done')

        report_play_result(roles)

    # 用户先自己开好游戏，然后程序来刷buff
    elif goal == 'shen_yuan_mo_ku':
        pos_list = await player.find_all_pos('setting')
        if not pos_list:
            return stop_play("请先开好游戏，让其停留在游戏主界面，然后再运行程序来刷深渊魔窟buff")

        for pos in pos_list:
            create_play_task(None, g_lock, g_sem,
                             emu.in_which_window(pos), g_queue)

        count = len(pos_list)
        while count > 0:
            status, window, role = await g_queue.get()
            count -= 1
            print('count', count)

        playsound('./sounds/end.mp3')
        end_t = time.time()
        cost_minute = int((end_t - start_t) / 60)
        logger.info(
            f'Done, 为您节省时间约{cost_minute}分钟。\n如果对现有buff不满意，可以退回到游戏主界面，然后运行程序重刷。')


def report_play_result(roles):
    done_roles = []
    undone_roles = []

    for role in roles.all_roles:
        counter = PlayCounter(role.game + '_' + role.user)
        count = counter.get('RenWu', 'count')
        if count > 0:
            done_roles.append(role)
        else:
            undone_roles.append(role)

    print(f"""
总体游戏账号数量：     {len(roles.all_roles)}
完成了每日任务的数量： {len(done_roles)}
未完成数量：           {len(undone_roles)}
""")

    if len(undone_roles) > 0:
        print("未完成的账号：")
        for role in undone_roles:
            print(role)
        print("\n建议早晚各运行一次，以便完成每日任务，并最大化收取资源。")


def create_play_task(role, g_lock, g_sem, window, g_queue):
    player = Player(g_lock=g_lock, g_sem=g_sem,
                    window=window, logger=make_logger(window.name))
    asyncio.create_task(play(goal, player, role, g_queue))
    logger.info(f'{role} running on {window.name}')


def stop_play(msg):
    logger.info(msg)
    if loop.is_running():
        loop.stop()


if __name__ == "__main__":
    freeze_support()

    if len(sys.argv) == 2:
        goal = sys.argv[1]
    else:
        goal = 'daily_play'

    loop = asyncio.get_event_loop()
    loop.create_task(main(goal))

    keyboard.add_hotkey('space', stop_play, args=(
        "User canceled, so stop playing.", ))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("User stoped, so exit.")
        if loop.is_running():
            loop.stop()
    except Exception as e:
        logger.error(str(e))
        logger.error("出错了！请稍后重试。如果错误重复出现，可向作者反馈。")

    tasks = asyncio.all_tasks(loop=loop)
    group = asyncio.gather(*tasks, return_exceptions=True)
    group.cancel()
    try:
        loop.run_until_complete(group)
    except asyncio.CancelledError:
        if loop.is_running():
            print("CancelledError, stop")
            loop.stop()
    loop.close()

    # 按任意键继续
    os.system('pause')
