import logging
from logging import handlers
from lib import tasks
from lib import helper
from lib import ui_data
from lib.player import Player
from lib import player_eye
from lib.read_cfg import read_account_cfg
from lib.start_game import start_emulator, game_started
from lib import auto_play
import signal
import keyboard
from multiprocessing import freeze_support
from time import sleep
import concurrent.futures
import asyncio
import os
import sys
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


async def test_tasks(cls_name):
    g_player_lock = asyncio.Lock()
    player = Player('left_top', g_player_lock=g_player_lock)
    player.load_role_cfg()
    obj = getattr(tasks, cls_name)(player)
    await obj.run()


if __name__ == '__main__':
    names = ['friend_boss', 'yi_jian_shang_zhen']
    asyncio.run(test_eye(names, threshold=0.8, verify=False))

    # asyncio.run(test_tasks('ShenYuanMoKu'))


# TODO 每个任务都要记录完成情况，以便后续检查是否有任务没做到（比如说识别失败）
# 任务本身不要考虑识别失败的问题，以简化逻辑（要考虑各个点识别失败的话就太复杂了）
