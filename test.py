import logging
from logging import handlers
from lib import tasks
from lib import helper
from lib import ui_data
from lib.game import Game
from lib.player import Player
from lib import player_eye
from lib.read_cfg import read_account_cfg
# from lib.start_game import start_emulator, game_started
from lib import emulator
# from lib import auto_play
from lib import auto_play2
from lib import windows
import signal
import keyboard
from multiprocessing import freeze_support
from time import sleep
import concurrent.futures
import asyncio
import os
import sys
from lib import role
from lib.windows import Window
from lib.role import Role
from lib.recorder import PlayCounter

# 切换到脚本所在目录
# 否则，基于相对路径的代码会出问题
main_dir = os.path.split(os.path.realpath(__file__))[0]
os.chdir(main_dir)
sys.path.insert(0, main_dir)


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


async def test_tasks(cls_name, func=None):
    g_player_lock = asyncio.Lock()
    window = Window('left_top')
    player = Player(window=window, g_lock=g_player_lock)
    role = Role(game='mo_shi_jun_tun', user='uu')
    await role.load_all_attributes()
    counter = PlayCounter(role.game + '_' + role.user)
    # player.load_role_cfg()

    obj = getattr(tasks, cls_name)(player, role.play_setting, counter)
    if func:
        await getattr(obj, func)()
    else:
        await obj.run()

async def test_emulator():
    window = windows.Window('full')
    player = Player(g_lock=asyncio.Lock(), window=window)

    e = emulator.Emulator(player)
    await e.start_emulator()

async def test_game(func):
    window = windows.Window('full')
    player = Player(g_lock=asyncio.Lock(), window=window)

    g = Game(player)
    await getattr(g, func)()

async def test_role():
    game = 'mo_shi_jun_tun'
    user = 'aa592729440'
    r = role.Role(game, user)
    await r.load_all_attributes()
    for i in dir(r):
        if not i.startswith('__'):
            print(i, getattr(r, i))

if __name__ == '__main__':
    # names = ['wu_jiao_xing']
    # asyncio.run(test_eye(names, threshold=0.8, verify=False))

    asyncio.run(test_tasks('TiaoZhanFuben'))

    # asyncio.run(test_emulator())

    # asyncio.run(test_role())

    # from lib import read_cfg
    # res = read_cfg.read_game_user()
    # print(res)


    pass


# TODO 每个任务都要记录完成情况，以便后续检查是否有任务没做到（比如说识别失败）
# 任务本身不要考虑识别失败的问题，以简化逻辑（要考虑各个点识别失败的话就太复杂了）
