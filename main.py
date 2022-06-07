# -*-coding:utf-8-*-
##############################################################################
# 模拟玩家，自动玩游戏，打怪升级、做任务。
# 最多支持同时模拟4位玩家
#
##############################################################################


from lib.player import Player
from lib.windows import Window
from lib.emulator import Emulator
import logging
from datetime import datetime
from logging import handlers
from lib.read_cfg import read_account_cfg, read_game_user
# from lib.start_game import start_emulator, game_started
from lib.auto_play import play
import signal
import keyboard
from multiprocessing import freeze_support
from time import sleep
import concurrent.futures
import asyncio
import os
import sys
from lib import emulator
from lib.role import Role

from lib.helper import main_dir, make_logger
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
    g_lock = asyncio.Lock()
    g_sem = asyncio.Semaphore(1)
    g_queue = asyncio.Queue()
    game_user_list = read_game_user()
    idle_list = [Role(g, u) for (g, u) in game_user_list]
    running_list = []
    done_list = []

    player = Player(g_lock=g_lock, window=Window('full'), logger=logger)
    e = emulator.Emulator(player)
    window_list = [Window(i) for i in ['left_top', 'left_down', 'right_top']]
    # window_list = [Window(i) for i in ['left_top']]
    if not await e.emulator_started():
        await e.start_emulator()
        async for w in e.wait_emulator_started(window_list):
            player = Player(g_lock=g_lock, g_sem=g_sem, window=w, logger=make_logger(w.name))
            logger.info(f'start to play on {w.name} 1')
            asyncio.create_task(play(goal, player, None, g_queue))
    else:
        for w in window_list:
            player = Player(g_lock=g_lock, g_sem=g_sem, window=w, logger=make_logger(w.name))
            logger.info(f'start to play on {w.name} 2')
            asyncio.create_task(play(goal, player, None, g_queue))

    if goal == 'daily_play':
        while True:
            status, window, role = await g_queue.get()

            if role in idle_list:
                idle_list.remove(role)

            if status == 'running':
                logger.info(f'{role} running')
                running_list.append(role)
            elif status == 'done':
                logger.info(f'{role} done')
                running_list.remove(role)
                done_list.append(role)
                if running_list == idle_list == []:
                    logger.info('Done')
                    break

                if idle_list:
                    role = idle_list.pop()
                    player = Player(g_lock=g_lock, g_sem=g_sem,
                                    window=window, logger=make_logger(window.name))
                    task = asyncio.create_task(play(goal, player, role, g_queue))


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
