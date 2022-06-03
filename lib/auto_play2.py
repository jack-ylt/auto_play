from hashlib import blake2b
import time
import os
import asyncio
import shutil
from datetime import datetime
import re
import random
import math
from operator import itemgetter
from collections import namedtuple
from cv2 import threshold
from playsound import playsound
import math

from lib.ui_data import SCREEN_DICT, OK_BUTTONS, GOOD_TASKS, CLOSE_BUTTONS
from lib.player import Player, FindTimeout, GameNotResponding
from lib import tasks
from lib.game import Game
from lib.recorder import PlayCounter
from lib.role import Role
# from lib import role

# from ui_data import SCREEN_DICT
# from player import Player, FindTimeout

import logging

TASK_DICT = {
    'daily_play': [
        'MeiRiRenWu',
        'XianShiJie',
        'YouJian',
        'HaoYou',
        'SheQvZhuLi',
        'TiaoZhanFuben',
        'GongHui',
        'MeiRiQianDao',
        'JueDiKongJian',
        'ShengCunJiaYuan',
        'YaoQingYingXion',
        'WuQiKu',
        'XingCunJiangLi',
        'ShiChang',
        'JingJiChang',
        'GuanJunShiLian',
        'YongZheFuBen',
        'XingYunZhuanPan',
        'RenWuLan',
        'VipShangDian',
        'YingXiongYuanZheng',
        'MiGong',
        'RenWu',
    ],
    'shen_yuan_mo_ku': ['ShenYuanMoKu', ],
}


class PlayException(Exception):
    pass


async def play(goal, player, role, g_queue):
    player.logger.info(f"start to play, role: {role}")

    failed_task = set()
    

    game = Game(player)
    if role is None:
        game_name = 'mo_shi_jun_tun'
    else:
        game_name = role.game
    
    name, pos = await player.monitor(['setting', 'emulator_started', 'recent_tasks', 'ye_sheng'])
    if name == 'setting':
        # 在游戏主界面
        pass
    elif name == 'emulator_started':
        # 在模拟器主界面
        await game.start_game(game_name)
    elif name == 'recent_tasks':
        # 在游戏其它界面
        await game.goto_main_interface(game_name)
    elif name == 'ye_sheng':
        # 模拟器正在启动中
        await player.monitor('emulator_started', timeout=60)
        await game.start_game(game_name)
    else:
        # 模拟器没开，或者用户把它最小化了
        raise PlayException('error in play')

    # 主控传了role，就切换登录，否则就用原有账号继续游戏
    if role is None:
        user = await game.get_account()
        role = Role(game_name, user)
        await role.load_all_attributes()
    else:
        await role.load_all_attributes()
        await game.switch_account_login(role.game, role.user, role.passwd)

    await g_queue.put(('running', player.window, role))

    counter = PlayCounter(role.game + '_' + role.user)
    task_list = TASK_DICT[goal]
    for cls_name in task_list:
        await game.goto_main_interface(role.game)

        player.logger.info("Start to run: " + cls_name)
        obj = getattr(tasks, cls_name)(player, role.play_setting, counter)
        try:
            await obj.run()
        except Exception as e:
            task_list.append(cls_name)
            player.logger.error(str(e))
            player.save_operation_pics(str(e))
            if cls_name not in failed_task:
                failed_task.add(cls_name)
            else:
                if game.restart_count < 2:
                    await game.restart_game(role.game)
                else:
                    player.logger.error('restart too many times, so exit')
                    break
        finally:
            counter.save_data()
        
    await g_queue.put(('done', player.window, role))


