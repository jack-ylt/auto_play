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

from auto_play import play
from player_eye import dispatch

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

formatter = logging.Formatter(
    '%(asctime)s   %(levelname)s  %(funcName)s:%(lineno)d  %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
errh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(errh)
logger.addHandler(ch)


def handler(signum, frame):
    print('SIGINT for PID=', os.getpid())


def init():
    signal.signal(signal.SIGINT, handler)


async def main(g_exe):
    g_queue = asyncio.Queue()
    g_event = asyncio.Event()
    g_found = dict()
    g_hand_lock = asyncio.Lock()
    g_player_lock = asyncio.Lock()

    await asyncio.gather(
        play("left_top", g_queue, g_event, g_found, g_hand_lock, g_player_lock),
        # play("left_down", g_queue, g_event,
        #      g_found, g_hand_lock, g_player_lock),
        # play("right_top", g_queue, g_event,
        #      g_found, g_hand_lock, g_player_lock),
        dispatch(g_exe, g_queue, g_event, g_found),
    )

if __name__ == "__main__":
    g_exe = concurrent.futures.ProcessPoolExecutor(
        max_workers=4, initializer=init)

    try:
        asyncio.run(main(g_exe))
    except KeyboardInterrupt:
        print('ctrl + c')
    finally:
        g_exe.shutdown()
