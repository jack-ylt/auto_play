# -*-coding:utf-8-*-
##############################################################################
# 模拟玩家，自动玩游戏，打怪升级、做任务。
# 最多支持同时模拟4位玩家
#
##############################################################################

import asyncio
import concurrent.futures
import os
import signal
import sys
from time import sleep
from multiprocessing import freeze_support
import keyboard

from auto_play import play
from player_eye import dispatch
from start_game import start_emulator, game_started
from read_cfg import read_account_cfg

from logging import handlers
import logging

# log 设置：先设置root logger, 然后再每个模块引入自己的logger（名字是自己的模块名，设置继承root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
fh = handlers.TimedRotatingFileHandler('logs/all_log.log', when='D')
fh.setLevel(logging.DEBUG)
errh = logging.FileHandler('logs/error_log.log')
errh.setLevel(logging.ERROR)
ch = logging.StreamHandler()

debug = True
if debug:
    ch.setLevel(logging.DEBUG)
else:
    ch.setLevel(logging.INFO)

# formatter = logging.Formatter(
#     '%(asctime)s   %(levelname)s  %(funcName)s:%(lineno)d  %(message)s')
formatter = logging.Formatter(
    '%(asctime)s   %(levelname)s   %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
errh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(errh)
logger.addHandler(ch)


class UserStop(Exception):
    """
    when user press blank button, raise 
    """
    pass


def handler(signum, frame):
    logger.info('SIGINT for PID=' + str(os.getpid()))


def init():
    signal.signal(signal.SIGINT, handler)


async def main(g_exe):
    if not game_started():
        await start_emulator()

    g_queue = asyncio.Queue()
    g_event = asyncio.Event()
    g_found = dict()
    g_player_lock = asyncio.Lock()
    account_list = read_account_cfg()

    await asyncio.gather(
        play("left_top", account_list, g_queue, g_event, g_found, g_player_lock),
        play("left_down", account_list, g_queue, g_event,
             g_found, g_player_lock),
        play("right_top", account_list, g_queue, g_event,
             g_found, g_player_lock),
        dispatch(g_exe, g_queue, g_event, g_found),
    )

def stop_play():
    raise UserStop()

if __name__ == "__main__":
    freeze_support()
    
    g_exe = concurrent.futures.ProcessPoolExecutor(
        max_workers=4, initializer=init)

    try:
        keyboard.add_hotkey('esc', stop_play)
        asyncio.run(main(g_exe))
    except KeyboardInterrupt:
        logger.info('ctrl + c')
    except UserStop:
        logger.info('user press esc')
    finally:
        g_exe.shutdown()
