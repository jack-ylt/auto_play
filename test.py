import logging
# from logging import handlers
from lib import tasks
# from lib import helper
from lib import ui_data
from lib.gamer import Gamer
from lib.player import FindTimeout, Player
from lib import player_eye
# from lib.read_cfg import read_account_cfg
# from lib.start_game import start_emulator, game_started
from lib import emulator
# from lib import auto_play
# from lib import auto_play
from lib import windows
# import signal
# import keyboard
# from multiprocessing import freeze_support
# from time import sleep
# import concurrent.futures
import asyncio
import os
import sys
import time
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


async def test_eye(name=None, threshold=0.8, verify=True, bbox=None):
    if not bbox:
        bbox = (0, 0, 905, 519)
        # bbox = None

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
    role_obj = Role(game='mo_shi_jun_tun', user='uu')
    await role_obj.load_all_attributes()
    counter = PlayCounter(role_obj.game + '_' + role_obj.user)
    # player.load_role_cfg()

    obj = getattr(tasks, cls_name)(player, role_obj.play_setting, counter)
    if func:
        await getattr(obj, func)()
    else:
        await obj.run()

# async def test_emulator():
#     window = windows.Window('full')
#     player = Player(g_lock=asyncio.Lock(), window=window)

#     e = emulator.Emulator(player)
#     await e.start_emulator()

async def test_gamer(func=None):
    window = windows.Window('left_top')
    player = Player(g_lock=asyncio.Lock(), window=window)

    g = Gamer(player)
    if func in ['restart', 'login']:
        r = role.Role('mo_shi_jun_tun', 'aa592729440')
        await getattr(g, func)(r)
    else:
        await getattr(g, func)()
    

async def test_role():
    game = 'mo_shi_jun_tun'
    user = 'aa592729440'
    r = role.Role(game, user)
    await r.load_all_attributes()
    for i in dir(r):
        if not i.startswith('__'):
            print(i, getattr(r, i))


async def findfile(start, name):
    if not os.path.isdir(start):
        return ''

    for path, dirs, files in os.walk(start):
        if name in files:
            full_path = os.path.join(start, path, name)
            full_path = os.path.normpath(os.path.abspath(full_path))
            return full_path
        await asyncio.sleep(0.2)
    return ''

async def find_emulator():
    from asyncio import as_completed
    name = 'MultiPlayerManager.exe'
    a_dir = 'Program Files'
    
    tasks = []
    for st in [r'C:\\', r'D:\\', r'E:\\', r'F:\\']:

        task = asyncio.create_task(findfile(st + a_dir, name))
        tasks.append(task)

    try:
        for coro in as_completed(tasks, timeout=50):
            earliest_result = await coro
            print(earliest_result)
            if os.path.isfile(earliest_result):
                print('find the file')
                return earliest_result
            else:
                print(f'result: {earliest_result}')
    except asyncio.TimeoutError:
        print('timeout, cant find the file')
        # ...

async def test_mouse():
    window = windows.Window('full')
    player = Player(g_lock=asyncio.Lock(), window=window)
    for i in range(5):
        await player.find_then_click(['close', 'fight7'], timeout=2)

        # player.hand.m.press(200, 10)
        player.hand.m.release(200, 10)
        await asyncio.sleep(2)

        # if i % 3 == 0:
        #     player.hand.m.press(450, 20)
        #     player.hand.m.release(450, 20)


if __name__ == '__main__':
    # names = ['guai1', 'guai2', 'guai3', 'guai4', 'guai5', 'guai6', 'guai7']
    # names = ['bao_xiang_guai', 'bao_xiang_guai1', 'bao_xiang_guai2', 'bao_xiang_guai3']
    names = ['xing_pian_bao_xiang']
    asyncio.run(test_eye(names, threshold=0.8, verify=False, bbox = (0, 0, 1920, 1080)))

    # asyncio.run(test_tasks('GuanJunShiLian'))

    # asyncio.run(test_emulator())

    # asyncio.run(test_role())

    # asyncio.run(test_mouse())

    # asyncio.run(test_gamer('restart'))

    # t1 = time.time()
    # asyncio.run(find_emulator())
    # t2 = time.time()
    # print(t2 - t1)

    # pass



# TODO 每个任务都要记录完成情况，以便后续检查是否有任务没做到（比如说识别失败）
# 任务本身不要考虑识别失败的问题，以简化逻辑（要考虑各个点识别失败的话就太复杂了）
