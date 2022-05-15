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
from lib import helper

from lib import tasks

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

async def test_eye(name=None, threshold=0.8, verify=True):
    # bbox = (0, 0, 1000, 540)
    bbox = None

    if name is None:
        name = ['boss', 'boss1', 'boss2']
        name = ui_data.OK_BUTTONS

    # 查找一个，大概0.1s，5个0.23s， 10个0.4s
    await player_eye.test(name, bbox, threshold, verify=verify)
    # eye = player_eye.Eye()
    # await eye.monitor(name)


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


async def test_market():
    g_player_lock = asyncio.Lock()
    player = Player('left_top', g_player_lock=g_player_lock)
    auto = auto_play.AutoPlay(player)

    # await auto._receive_survival_reward()
    # await auto._buy_goods()
    await auto.market()
    

async def test_brave_instance(auto):
    await auto.brave_instance()



async def test_drag(auto):
    for i in range(3):
        for j in [
            '_move_to_left_top',
            '_move_to_right_top',
            '_move_to_left_down',
            '_move_to_center',
        ]:
            print(j)
            await auto.__getattribute__(j)()
            await asyncio.sleep(2)

async def test_auto_play():
    g_player_lock = asyncio.Lock()
    player = Player('left_top', g_player_lock=g_player_lock)
    auto = auto_play.AutoPlay(player)
    
    # await auto.survival_home()
    # await auto.tower_battle()
    # await auto.guild()
    # await auto.restart_game()
    # await auto.level_battle()
    # await auto.arena_champion()
    # print(await auto.player.is_disabled_button((315, 408)))
    # await test_brave_instance(auto)
    # await test_drag(auto)
    # await auto.goto_main_interface()
    # await auto.market()
    # await auto.shen_yuan_mo_ku()
    # await auto.instance_challenge()
    # await auto._move_to_right_down()
    # await auto.ju_dian_gong_hui_zhan()
    await auto.invite_heroes()

async def test_tasks(cls_name):
    g_player_lock = asyncio.Lock()
    player = Player('left_top', g_player_lock=g_player_lock)
    player.load_role_cfg()
    obj = getattr(tasks, cls_name)(player)
    await obj.run()


if __name__ == '__main__':
    # names = ['max1', 'yi_jian_shang_zhen'] 
    # asyncio.run(test_eye(names, threshold=0.8, verify=False))

    # asyncio.run(test_auto_play())

    asyncio.run(test_tasks('YingXiongYuanZheng'))


# TODO 每个任务都要记录完成情况，以便后续检查是否有任务没做到（比如说识别失败）
# 任务本身不要考虑识别失败的问题，以简化逻辑（要考虑各个点识别失败的话就太复杂了）