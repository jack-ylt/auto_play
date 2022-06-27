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

from lib import emulator
from lib.auto_play import play
from lib.helper import main_dir, make_logger
from lib.player import Player
from lib.read_cfg import read_game_user
from lib.role import Role, Roles
from lib.windows import Window
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
    roles = Roles()

    player = Player(g_lock=g_lock, window=Window('full'), logger=logger)
    emu = emulator.Emulator(player)

    async for window in emu.start_all_emulator():
        a_role = roles.get_idle_role()
        if a_role:
            create_play_task(a_role, g_lock, g_sem, window, g_queue)
        else:
            break

    if goal == 'daily_play':
        while True:
            status, window, role = await g_queue.get()

            if status == 'done':
                logger.info(f'{role} done on {window.name}')
                roles.set_role_status(role, 'done')

                if roles.is_all_roles_done():
                    playsound('./sounds/end.mp3')
                    end_t = time.time()
                    cost_hour = int((end_t - start_t) / 60)
                    logger.info(f'Done, 为您节省时间约{cost_hour}分钟。')
                    break

                # a_role = roles.get_idle_role(game=role.game) or roles.get_idle_role()
                a_role = roles.get_idle_role()
                if a_role:
                    create_play_task(a_role, g_lock, g_sem, window, g_queue)
            else:
                # 比如验证码出来了，所以就换个账号登陆
                logger.warning(f'{role} run error on {window.name}')
                a_role = roles.get_idle_role()
                if a_role:
                    create_play_task(a_role, g_lock, g_sem, window, g_queue)
                roles.set_role_status(role, 'idle')


def create_play_task(role, g_lock, g_sem, window, g_queue):
    player = Player(g_lock=g_lock, g_sem=g_sem,
                    window=window, logger=make_logger(window.name))
    asyncio.create_task(play(goal, player, role, g_queue))
    logger.info(f'{role} running on {window.name}')


def stop_play():
    logger.info("User canceled, so exit.")
    if loop.is_running():
        loop.stop()


if __name__ == "__main__":
    freeze_support()

    if len(sys.argv) == 2:
        goal = sys.argv[1]
    else:
        goal = 'daily_play'
        # goal = 'shen_yuan_mo_ku'

    loop = asyncio.get_event_loop()
    loop.create_task(main(goal))

    keyboard.add_hotkey('space', stop_play)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("User stoped, so exit.")
        if loop.is_running():
            loop.stop()

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
