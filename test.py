
import asyncio
import logging
import os
import sys

from lib import player_eye, role, ui_data, windows
from lib.gamer import Gamer
from lib.player import Player
from lib.recorder import PlayCounter
from lib.role import Role
from lib.windows import Window

# from lib import tasks
import tasks


# 切换到脚本所在目录
# 否则，基于相对路径的代码会出问题
main_dir = os.path.split(os.path.realpath(__file__))[0]
os.chdir(main_dir)
sys.path.insert(0, main_dir)


logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)

# formatter = logging.Formatter(
#     '%(asctime)s   %(levelname)s   %(message)s')
# ch.setFormatter(formatter)
# logger.addHandler(ch)


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


async def test_tasks(cls_name, func=None, args=[]):
    g_player_lock = asyncio.Lock()
    window = Window('left_top')
    player = Player(window=window, g_lock=g_player_lock)
    role_obj = Role(game='mo_ri_qian_xian', user='uu')
    await role_obj.load_all_attributes()
    counter = PlayCounter(role_obj.game + '_' + role_obj.user)
    # player.load_role_cfg()

    # obj = getattr(tasks, cls_name)(player, role_obj.play_setting, counter)
    obj = getattr(tasks, cls_name)(player, role_obj.play_setting, counter)
    
    try:
        if func:
            await getattr(obj, func)(*args)
        else:
            await obj.run()
    except Exception as err:
        # player.save_operation_pics(str(err))
        print(err)
        raise

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
        r = role.Role('mo_ri_qian_xian', 'aa592729440')
        r.load_all_attributes()
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

def test_text_recognition(area):
    # eye = player_eye.Eye()
    # area = (395, 153, 503, 183)
    # text = eye.get_text(area)
    # print(text)
    window = windows.Window('left_top')
    player = Player(g_lock=asyncio.Lock(), window=window)
    # area = (395, 153, 503, 183)
    # area = (210, 215, 370, 280)
    # area = (220, 335, 335, 370)
    # area = (668, 205, 720, 235)
    # area =(390, 39, 470, 68)


    text = player.get_text(area)
    print(text)



if __name__ == '__main__':
    # names =  [ 'aaa2']
    # asyncio.run(test_eye(names, threshold=0.9, verify=False, bbox = (0, 0, 1920, 1080)))

    asyncio.run(test_tasks('JueDiQiuSheng'))
    # asyncio.run(test_tasks('GuanJunShiLian', func='_get_enemy_score', args=[0]))
    # asyncio.run(test_gamer('restart'))

    # area = (407, 378, 465, 430)
    # test_text_recognition(area)





# TODO 每个任务都要记录完成情况，以便后续检查是否有任务没做到（比如说识别失败）
# 任务本身不要考虑识别失败的问题，以简化逻辑（要考虑各个点识别失败的话就太复杂了）
