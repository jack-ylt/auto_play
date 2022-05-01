# -*-coding:utf-8-*-
##############################################################################
# 模拟玩家，自动玩游戏，打怪升级、做任务。
# 最多支持同时模拟4位玩家
#
##############################################################################


import os
import sys
# 切换到脚本所在目录
# 否则，基于相对路径的代码会出问题

# print(__file__)
# print(os.path.realpath(__file__))
# print(sys.argv[0])
# print(sys.path[0])
# print(os.path.dirname(os.path.realpath(sys.argv[0])))

# main_dir = os.path.split(os.path.realpath(__file__))[0]

# 打成单文件，只有这个打包前后路径是一致的
# main_dir = os.path.dirname(os.path.realpath(sys.executable))

from lib.helper import main_dir

os.chdir(main_dir)
sys.path.insert(0, main_dir)


import asyncio
import concurrent.futures

from time import sleep
from multiprocessing import freeze_support
import keyboard
import signal
from lib.auto_play import play
from lib.start_game import start_emulator, game_started
from lib.read_cfg import read_account_cfg

from logging import handlers
from datetime import datetime
import logging



# log 设置：先设置root logger, 然后再每个模块引入自己的logger（名字是自己的模块名，设置继承root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
today = datetime.now().strftime(r'%Y-%m-%d')
all_log = os.path.join(main_dir, 'logs', 'all_log_' + today + '.log')
fh = handlers.TimedRotatingFileHandler(all_log, when='D', interval=1, backupCount=7)
# fh = handlers.RotatingFileHandler('logs/all_log.log', mode='a', maxBytes=5*1024*1024, backupCount=3)
fh.setLevel(logging.DEBUG)
errh = logging.FileHandler(main_dir + '/logs/error_log.log')
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
    if not await game_started():
        await start_emulator()

    g_queue = asyncio.Queue()
    g_event = asyncio.Event()
    g_found = dict()
    g_player_lock = asyncio.Lock()
    g_sem = asyncio.Semaphore(1)
    account_list = read_account_cfg()

    await asyncio.gather(
        play("left_top", account_list, g_queue, g_event, g_found, g_player_lock, g_sem),
        play("left_down", account_list, g_queue, g_event,
             g_found, g_player_lock, g_sem),
        play("right_top", account_list, g_queue, g_event,
             g_found, g_player_lock, g_sem),
    )

def stop_play():
    logger.info("User canceled, so exit.")
    if loop.is_running():
        loop.stop()

if __name__ == "__main__":
    freeze_support()
    
    g_exe = concurrent.futures.ProcessPoolExecutor(
        max_workers=4, initializer=init)

    # try:
    #     keyboard.add_hotkey('esc', stop_play)
    #     asyncio.run(main(g_exe))
    # except KeyboardInterrupt:
    #     logger.info('ctrl + c')
    # except UserStop:
    #     logger.info('user press esc')
    # finally:
    #     g_exe.shutdown()

    loop = asyncio.get_event_loop()
    loop.create_task(main(g_exe))

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

