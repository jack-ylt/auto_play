import os
import sys
# 切换到脚本所在目录
# 否则，基于相对路径的代码会出问题
main_dir = os.path.split(os.path.realpath(__file__))[0]
os.chdir(main_dir)
sys.path.insert(0, main_dir)


import asyncio
import concurrent.futures

from time import sleep
from multiprocessing import freeze_support
import keyboard
import signal
from lib import auto_play
from lib.start_game import start_emulator, game_started
from lib.read_cfg import read_account_cfg
from lib import player_eye
from lib.player import Player
from lib import ui_data

from logging import handlers
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s   %(levelname)s   %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

async def test_eye(name=None):
    bbox = (0, 0, 1000, 540)
    # bbox = None

    if name is None:
        name = ['boss', 'boss1', 'boss2']
        name = ui_data.OK_BUTTONS

    # 查找一个，大概0.1s，5个0.23s， 10个0.4s
    await player_eye.test(name, bbox)


async def test_survival_home():
    g_player_lock = asyncio.Lock()
    player = Player('left_top', g_player_lock=g_player_lock)
    auto = auto_play.AutoPlay(player)

    # c = await auto._get_total_floors()
    # print(c)

    # await auto._goto_floor(6)

    # for d in ['left_top',
    #         'left_down',
    #         'right_down',
    #         'right_top']:
    #     await auto._swip_to(d)
    #     await asyncio.sleep(1)

    # c = await auto._fight_home_boos(3, 5)
    # print(c)

    await auto.survival_home()

async def test_task_board():
    g_player_lock = asyncio.Lock()
    player = Player('left_top', g_player_lock=g_player_lock)
    auto = auto_play.AutoPlay(player)
    
    # for i in range(5):
    #     for i in range(2):
    #         await auto._swip_to('right', stop=True)
    #     for i in range(2):
    #         await auto._swip_to('left', stop=True)

    # await auto._accept_task()

    # await auto._finish_all_tasks()
    
    await auto.task_board()

if __name__ == '__main__':
    # sleep(1)
    # asyncio.run(test_eye('all_received'))
    # asyncio.run(test_survival_home())
    asyncio.run(test_task_board())