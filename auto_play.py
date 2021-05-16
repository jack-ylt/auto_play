# -*-coding:utf-8-*-
##############################################################################
# 模拟玩家，自动玩游戏，打怪升级、做任务。
#
##############################################################################

import concurrent.futures
from multiprocessing import Process, Manager, Pool
import time
import os
import asyncio
import sys
import signal
import shutil
import datetime
import re
import math
import random
from operator import itemgetter

import player_eye
import player_hand

# log 设置：先设置root logger, 然后再每个模块引入自己的logger（名字是自己的模块名，设置继承root logger
import logging
from logging import handlers
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
fh = handlers.TimedRotatingFileHandler('logs/all_log.log', when='D')
fh.setLevel(logging.DEBUG)
errh = logging.FileHandler('logs/error_log.log')
errh.setLevel(logging.ERROR)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s   %(levelname)s  %(funcName)s:%(lineno)d  %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
errh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(errh)
logger.addHandler(ch)


eye = player_eye.Eye()
hand = player_hand.Hand()


#
# stop script
#
class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass


def service_shutdown(signum, frame):
    logger.debug('Caught signal %d' % signum)
    raise ServiceExit


class FindTimeout(Exception):
    """
    when no found and timeout, raise 
    """
    pass


def filter_rightmost(pos_list):
    """get the rightmost position"""
    pos = max(pos_list)
    return pos

def filter_first(pos_list):
    pos = pos_list[0]
    return pos


def filter_bottom(pos_list):
    lst = sorted(pos_list, key=lambda x: x[1])
    pos = lst[-1]
    return pos


async def monitor(names, threshold=0.9, timeout=5, filter_func=filter_first):
    """return (name, pos), all rease timeout_error"""
    start_time = time.time()
    logger.debug(f'start monitor: {names}')

    count = 0
    result = None
    while time.time() - start_time < timeout:
        # logger.debug(f'count: {count}')
        count += 1
        # player_hand.m.move(-10, -10)    # hide the mouse
        # 移走鼠标，很难结束程序
        screen = eye.screenshot(player_eye.PIC_DICT['screen'])
        screen_dict['screen'] = screen
        for name in names:
            find_queue.put((name, threshold))

        await asyncio.sleep(0.5)

        for _ in range(len(names)):
            name, pos_list = found_queue.get()
            # logger.debug(f'name: {name} pos: {pos}')
            if pos_list:
                logger.debug(f'found {name} at {pos_list}')
                pos = filter_func(pos_list)
                result = (name, pos)

        if result:
            return result

    msg = (f"monitor {names} timeout. ({timeout} s)")
    logger.debug(msg)
    raise FindTimeout(msg)


async def find_all_pos(names, threshold=0.8):
    """return list of pos"""
    logger.debug(f'start find all positions of: {names}')

    all_pos = []

    screen = eye.screenshot(player_eye.PIC_DICT['screen'])
    screen_dict['screen'] = screen
    for name in names:
        find_queue.put((name, threshold))

    await asyncio.sleep(0.5)

    for _ in range(len(names)):
        name, pos_list = found_queue.get()
        if pos_list:
            all_pos.extend(pos_list)

    # 多个pic的情况下，可能会有重合
    all_pos = eye.de_duplication(all_pos)

    if all_pos:
        logger.debug(f'find_all_pos of {names} at {all_pos}')
    else:
        logger.debug(f'no find any pos of {names}')

    return all_pos


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


async def move_to_left_top():
    logger.debug('move_to_left_top')
    p1 = (200, 300)
    p2 = (800, 400)
    await hand.drag(p1, p2)


async def move_to_right_top():
    logger.debug('move_to_right_top')
    p1 = (700, 200)
    p2 = (200, 400)
    await hand.drag(p1, p2)
    await hand.drag(p1, p2)


async def move_to_center():
    logger.debug('move_to_center')
    await move_to_left_top()
    p1 = (500, 300)
    p2 = (200, 300)
    await hand.drag(p1, p2)


async def move_to_left_down():
    logger.debug('move_to_left_down')
    p1 = (200, 400)
    p2 = (700, 200)
    await hand.drag(p1, p2)


async def goto_main_interface():
    for _ in range(5):
        try:
            _, pos = await monitor(['setting'], timeout=1)
            # await hand.click((855, 45), cheat=False)    # 去掉一些遗留界面
            break
        except FindTimeout:
            await hand.tap_key(player_hand.k.escape_key, delay=1)
    else:
        msg = "goto main interface failed"
        logger.error(msg, exc_info=True)
        raise FindTimeout(msg)


def eye_woker(find_queue, screen_dict, found_queue):
    while True:
        try:
            if not find_queue.empty():
                item = find_queue.get()
                if item == 'STOP':
                    logger.debug('get STOP, so exit')
                    break
                name, threshold = item
                # logger.info(f'{name}, {threshold}, {filter_func}')
                img = eye.img_dict[name]
                img_bg = screen_dict['screen']
                pos_list = eye.find_img_pos(img_bg, img, threshold)
                found_queue.put((name, pos_list))
            time.sleep(0.2)
        except KeyboardInterrupt:
            logger.info('eye_woker stoped by user')
        except Exception as e:
            logger.error(str(e), exc_info=True)
            break


async def fight():
    """do fight, return win or lose"""
    _, pos = await monitor(['start_fight', 'fight1'])
    await hand.click(pos, delay=3)

    try:
        _, pos = await monitor(['fast_forward1'], timeout=1)
        await hand.click(pos)
    except FindTimeout:
        pass

    await asyncio.sleep(10)

    name, pos = await monitor(['go_last', 'win', 'lose'], timeout=180)
    if name == 'go_last':
        await hand.click(pos)
        name, pos = await monitor(['win', 'lose'], timeout=180)
    pos_ok = (430, 430)
    await hand.click(pos_ok, delay=3)

    return name


async def nextlevel_to_fight(pos):
    """go from next_level to fight"""
    await hand.click(pos)
    try:
        name, pos = await monitor(['search', 'level_map'])
    except FindTimeout:
        return False
        # 打到当前等级的关卡上限了
    if name == 'search':
        await hand.click(pos)
        await asyncio.sleep(10)    # TODO vip no need 10s
    else:
        await asyncio.sleep(3)
        _, pos = await monitor(['point'], threshold=0.9, filter_func=filter_rightmost)
        await hand.click((pos[0] + 50, pos[1]))    # 往右偏移一点，刚好能点击进入到下一个大关卡
        _, pos = await monitor(['ok1'])
        await hand.click(pos)
        await asyncio.sleep(10)

    _, pos = await monitor(['fight'])
    await hand.click(pos)
    return True


async def passed_to_fight():
    """go from already_passed to fight"""
    try:
        name, pos = await monitor(['next_level2', 'next_level3'], threshold=0.85)
    except FindTimeout:
        return False
    await hand.click(pos, cheat=False)
    _, pos = await monitor(['search'])
    await hand.click(pos)
    await asyncio.sleep(10)
    _, pos = await monitor(['fight'])
    await hand.click(pos)
    return True


async def hand_upgraded():

    await asyncio.sleep(5)

    try:
        _, pos = await monitor(['map_unlocked'])
    except FindTimeout:
        pass
    else:
        await hand.click(pos)
        await asyncio.sleep(5)
        await goto_main_interface()
        await move_to_center()
        _, pos = await monitor(['level_battle'])
        await hand.click(pos, delay=3)
    finally:
        name, pos = await monitor(['next_level1', 'already_passed', 'fight'])

    return (name, pos)


async def level_battle():
    """关卡战斗"""
    await move_to_center()
    name, pos = await monitor(['level_battle'])
    await hand.click(pos, delay=3)

    pos_box = (750, 470)
    await hand.click(pos_box)
    try:
        _, pos = await monitor(['receive'])
        await hand.click(pos)
    except FindTimeout:
        pass

    name, pos = await monitor(['upgraded', 'next_level1', 'already_passed', 'fight'])
    if name == 'upgraded':
        name, pos = await hand_upgraded()

    if name == 'next_level1':
        success = await nextlevel_to_fight(pos)
        if not success:
            return await goto_main_interface()
    elif name == 'already_passed':
        success = await passed_to_fight()
        if not success:
            return await goto_main_interface()
    else:
        await hand.click(pos)

    while True:
        res = await fight()

        if res == 'lose':
            logger.debug('Fight fail, so exit')
            # 打不过，就需要升级英雄，更新装备了
            return await goto_main_interface()

        name, pos = await monitor(['upgraded', 'next_level1'])
        if name == 'upgraded':
            name, pos = await hand_upgraded()

        await nextlevel_to_fight(pos)


async def tower_battle():
    await asyncio.sleep(1)
    await move_to_right_top()

    _, pos = await monitor(['warriors_tower'])
    await hand.click(pos, delay=2)
    pos_list = [
        (150, 360),
        (400, 360),
        (650, 360),
    ]

    while True:
        for pos in pos_list:
            await hand.click(pos, delay=0.2)
        await asyncio.sleep(1)

        _, pos = await monitor(['challenge'])
        await hand.click(pos)

        res = await fight()

        if res == 'lose':
            logger.debug('Fight fail, so exit')
            # 打不过，就需要升级英雄，更新装备了
            return await goto_main_interface()


def save_timeout_pic(msg):
    screen_pic = player_eye.PIC_DICT['screen']
    timestr = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    monitor_items = re.search(r'\[.+\]', msg).group()
    log_pic = os.path.join('./timeout_pics', f"{timestr}_{monitor_items}.jpg")
    shutil.copyfile(screen_pic, log_pic)
    logger.info(f"save_timeout_pic: {monitor_items}")


async def collect_mail():
    try:
        _, pos = await monitor(['mail'], threshold=0.97, timeout=1)
    except FindTimeout:
        logger.debug("There is no new mail.")
        return
    await hand.click(pos)
    _, pos = await monitor(['one_click_collection'])
    await hand.click(pos)
    await goto_main_interface()

async def fight_friend(max_try=3):
    max_try = max_try
    count = 0
    pos_ok_win = (430, 430)
    pos_ok_lose = (340, 430)
    pos_next = (530, 430)
    _, pos_fight = await monitor(['start_fight'])
    try:
        await monitor(['skip_fight'], threshold=0.97, timeout=1)
        skip_fight = True
    except FindTimeout:
        skip_fight = False

    await hand.click(pos_fight)

    while True:
        count += 1
        if not skip_fight:
            await asyncio.sleep(3)
            # 25级以下无法加速，60以下无法快进
            for _ in range(3):
                pos_list = await find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
                if pos_list:
                    for pos in pos_list:
                        await hand.click(pos)
                    break
                await asyncio.sleep(1)
        _, pos = await monitor(['card'], timeout=180)
        await hand.click(pos)    # 卡片点两次，才会消失
        await hand.click(pos)
        fight_res, pos = await monitor(['win', 'lose'])
        if fight_res == 'win':
            await hand.click(pos_ok_win)
            break
        else:
            if count < max_try:
                await hand.click(pos_next)
            else:
                await hand.click(pos_ok_lose)
                break

    if not skip_fight:
        await asyncio.sleep(3)
    return fight_res


async def friends_interaction():
    try:
        _, pos = await monitor(['friends'], threshold=0.97, timeout=1)
    except FindTimeout:
        logger.debug("There is no new interaction of friends.")
        return

    await hand.click(pos)
    _, pos = await monitor(['receive_and_send'])
    await hand.click(pos)

    try:
        _, pos = await monitor(['friends_help'], threshold=0.97, timeout=1)
    except FindTimeout:
        logger.debug("There is no friend need help.")
        await goto_main_interface()
        return

    await hand.click(pos)

    while True:
        try:
            _, pos = await monitor(['search1'], threshold=0.97, timeout=1)
            await hand.click(pos)
        except FindTimeout:
            logger.debug("There is no more boss.")
            await goto_main_interface()
            return

        _, pos = await monitor(['fight2'])
        await hand.click(pos)
        _, pos = await monitor(['fight3'])
        await hand.click(pos)

        res = await fight_friend()
        if res != 'win':
            logger.debug("Can't win the boos")
            await goto_main_interface()
            return


async def community_assistant():
    _, pos = await monitor(['community_assistant'])
    await hand.click(pos)

    try:
        _, pos = await monitor(['guess_ring'], threshold=0.97, timeout=1)
    except FindTimeout:
        logger.debug("Fress guess had been used up.")
        await goto_main_interface()
        return
    await hand.click(pos)

    _, pos = await monitor(['cup'])
    await hand.click(pos)
    for _ in range(2):
        _, pos = await monitor(['next_game'])
        await hand.click(pos)
        _, pos = await monitor(['cup'])
        await hand.click(pos)
        _, pos = await monitor(['next_game'])
    await hand.tap_key(player_hand.k.escape_key, delay=1)
    try:
        _, pos = await monitor(['have_a_drink'])
        await hand.click(pos)
    except FindTimeout:
        pass

    _, pos = await monitor(['gift'])
    await hand.click(pos)
    pos_select_gift = (70, 450)
    pos_send_gift = (810, 450)
    while True:
        try:
            _, pos = await monitor(['gift_over'], threshold=0.97, timeout=1)
            break
        except FindTimeout:
            await hand.click(pos_select_gift, delay=0.2)
            await hand.click(pos_send_gift)
            try:
                _, pos = await monitor(['start_turntable'], timeout=1)
                await hand.click(pos)
                await asyncio.sleep(5)
            except FindTimeout:
                pass

    await goto_main_interface()


async def fight_challenge():
    # 25级以下无法加速，60以下无法快进
    for _ in range(3):
        pos_list = await find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
        if pos_list:
            for pos in pos_list:
                await hand.click(pos)
            break
        await asyncio.sleep(1)

    fight_res, pos = await monitor(['win', 'lose'], timeout=180)
    return fight_res


async def instance_challenge():
    try:
        _, pos = await monitor(['Instance_challenge'], threshold=0.98, timeout=1)
        await hand.click(pos)
    except FindTimeout:
        logger.debug("No new challenge.")
        return
    
    challenge_list = await find_all_pos(['challenge2'], threshold=0.93)
    pos_ok = (430, 430)
    pos_next = (530, 430)
    for pos in challenge_list:
        await hand.click(pos)
        pos_list = await find_all_pos(['challenge3', 'mop_up'])
        pos = filter_bottom(pos_list)
        await hand.click(pos)
        name, pos = await monitor(['start_fight', 'next_game1'])
        await hand.click(pos)
        if name == 'start_fight':
            await asyncio.sleep(3)
            res = await fight_challenge()
            if res != 'win':
                logger.debug("Fight lose")
            else:
                await hand.click(pos_next, delay=3)
                await fight_challenge()
            await hand.click(pos_ok, delay=3)
        else:
            await hand.click(pos_next)
            await hand.click(pos_ok)
            
        await hand.tap_key(player_hand.k.escape_key, delay=1)
    
    await goto_main_interface()


async def fight_guild():
    _, pos = await monitor(['start_fight'])
    await hand.click(pos, delay=3)
    pos_list = await find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
    for pos in pos_list:
        await hand.click(pos)
    _, pos = await monitor(['ok'], timeout=180)
    await hand.click(pos, delay=3)

async def guild():
    try:
        _, pos = await monitor(['guild'], threshold=0.97, timeout=1)
        await hand.click(pos)
    except FindTimeout:
        logger.debug("No new guild event.")
        return

    try:
        _, pos = await monitor(['sign_in'], threshold=0.97, timeout=1)
        await hand.click(pos)
    except:
        pass
    pos_guild_territory = (700, 460)
    await hand.click(pos_guild_territory)

    # guild_instance
    _, pos = await monitor(['guild_instance'])
    await hand.click(pos)
    try:
        _, pos = await monitor(['boss_card'], threshold=0.92, timeout=1)
        # 匹配的是卡片边缘，而需要点击的是中间位置
        pos = (pos[0], pos[1]+50)
        await hand.click(pos)
        _, pos = await monitor(['fight4', 'fight5'], threshold=0.97, timeout=1)
        await hand.click(pos)
        await fight_guild()
    except FindTimeout:
        pass

    # guild_factory
    while True:
        await hand.tap_key(player_hand.k.escape_key, delay=1)
        try:
            _, pos = await monitor(['guild_factory'], timeout=1)
            await hand.click(pos)
            break
        except FindTimeout:
            pass

    # 进入再退出，可以消除订单完成的弹出框
    await hand.tap_key(player_hand.k.escape_key, delay=1)
    _, pos = await monitor(['guild_factory'])
    await hand.click(pos)
    _, pos = await monitor(['get_order'])
    await hand.click(pos)
    pos_list = await find_all_pos(['start_order'])
    for pos in pos_list:
        await hand.click(pos)
    await move_to_right_top()
    pos_list = await find_all_pos(['start_order'])
    for pos in pos_list:
        await hand.click(pos)

    # Donate
    pos_donate_home = (770, 270)
    await hand.click(pos_donate_home)
    _, pos = await monitor(['donate'])
    await hand.click(pos)
    try:
        _, pos = await monitor(['ok5'], timeout=1)
        await hand.click(pos)
    except:
        pass

    # open boxes
    pos_boxes = [
        (200, 170),
        (310, 170),
        (540, 170),
        (700, 170),
    ]
    for p in pos_boxes:
        await hand.click(p)
        try:
            _, pos = await monitor(['ok4'], timeout=1)
            await hand.click(pos)
        except:
            pass

    await goto_main_interface()


async def exciting_activities():
    pos_exciting_activities = (740, 70)
    await hand.click(pos_exciting_activities)
    pos_sign_in = (700, 430)
    await hand.click(pos_sign_in)
    await goto_main_interface()


async def jedi_space():
    await move_to_left_top()
    _, pos = await monitor(['jedi_space'])
    await hand.click(pos)

    pos_challenge = (430, 450)
    await hand.click(pos_challenge)
    pos_mop_up = (650, 150)
    await hand.click(pos_mop_up)

    # done 这里要改成图像识别，因为点击pos_mop_up的结果不是确定的
    try:
        _, pos_plus = await monitor(['plus'], threshold=0.98, timeout=1)
    except FindTimeout:
        return await goto_main_interface()
    for _ in range(5):
        await hand.click(pos_plus, cheat=False, delay=0.2)
    pos_ok = (420, 360)
    await hand.click(pos_ok)

    await goto_main_interface()


async def fight_home(max_try=3):
    max_try = max_try
    count = 0
    pos_ok_win = (430, 430)
    pos_ok_lose = (340, 430)
    pos_next = (530, 430)
    _, pos_fight = await monitor(['start_fight'])
    try:
        await monitor(['skip_fight'], threshold=0.97, timeout=1)
        skip_fight = True
    except FindTimeout:
        skip_fight = False

    await hand.click(pos_fight)

    while True:
        count += 1
        if not skip_fight:
            await asyncio.sleep(3)
            # 25级以下无法加速，60以下无法快进
            for _ in range(3):
                pos_list = await find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
                if pos_list:
                    for pos in pos_list:
                        await hand.click(pos)
                    break
                await asyncio.sleep(1)
        fight_res, pos = await monitor(['win', 'lose'], timeout=180)
        if fight_res == 'win':
            await hand.click(pos_ok_win)
            break
        else:
            if count < max_try:
                await hand.click(pos_next)
            else:
                await hand.click(pos_ok_lose)
                break

    if not skip_fight:
        await asyncio.sleep(3)
    return fight_res


async def survival_home():
    await move_to_left_top()
    _, pos = await monitor(['survival_home'])
    await hand.click(pos, delay=3)

    pos_list = await find_all_pos(['food', 'gold', 'oil'])
    for pos in pos_list:
        await hand.click(pos, delay=0.2)

    pos_fight = (830, 490)
    await hand.click(pos_fight)

    # collect box
    _, pos = await monitor(['switch_map'])
    await hand.click(pos)
    for num in [-3, 3]:
        await hand.move(50, 350)
        await hand.scroll(num)
        map_list = await find_all_pos(['field_map'])
        map_list = sorted(map_list, key=lambda x: x[1], reverse=True)
        for pos in map_list:
            await hand.click(pos, delay=2)
            pos_list = await find_all_pos(['box'])
            for p1 in pos_list:
                await hand.click(p1, delay=0.2)

    # fight boss
    skip_last_map = False
    for num in [-3, 3]:
        await hand.move(50, 350)
        await hand.scroll(num)
        map_list = await find_all_pos(['field_map'])
        map_list = sorted(map_list, key=lambda x: x[1], reverse=True)

        # 一般，最下那层是打不过的
        if not skip_last_map:
            if len(map_list) > 1:
                new_map_list = map_list[1:]
                skip_last_map = True
            else:
                new_map_list = map_list
        else:
            new_map_list = map_list

        for pos in new_map_list:
            await hand.click(pos, delay=2)
            pos_list = await find_all_pos(['boss'])
            for p1 in pos_list:
                await hand.click(p1, cheat=False)
                _, p2 = await monitor(['fight6'])
                await hand.click(p2)
                res = await fight_home()
                if res != 'win':
                    # 打不过，就去打上一层
                    break
            # 战斗后，地图会缩回去
            if pos_list:
                _, pos = await monitor(['switch_map'])
                await hand.click(pos)
                                
    await goto_main_interface()


async def dismiss_heroes():
    _, pos = await monitor(['dismiss_hero'])
    await hand.click(pos, delay=2)
    pos_1 = (520, 425)
    pos_2 = (580, 425)
    pos_put_into = (150, 440)
    pos_dismiss = (320, 440)

    await hand.click(pos_1)
    await hand.click(pos_put_into)
    await hand.click(pos_dismiss)
    try:
        _, pos = await monitor(['receive1'], timeout=1)
        await hand.click(pos)
    except FindTimeout:
        pass

    await hand.click(pos_2)
    await hand.click(pos_put_into)
    await hand.click(pos_dismiss)
    try:
        _, pos = await monitor(['receive1'], timeout=1)
        await hand.click(pos)
    except FindTimeout:
        pass

    await goto_main_interface()

async def invite_heroes():
    await move_to_left_down()
    _, pos = await monitor(['invite_hero'])
    await hand.click(pos, delay=2)
    pos_list = await find_all_pos(['invite_free', 'invite_soda', 'invite_beer'])
    
    for pos in pos_list:
        await hand.click(pos)
        name, pos = await monitor(['ok6', 'close'])
        await hand.click(pos)
        # 如果英雄列表满了，就遣散英雄
        if name == 'close':
            await goto_main_interface()
            await dismiss_heroes()
            _, pos = await monitor(['invite_hero'])
            await hand.click(pos, delay=2)
        
    await goto_main_interface()


async def armory():
    # "armory": "./pics/armory/armory.jpg",
    # "arms": "./pics/armory/arms.jpg",
    await move_to_right_top()
    _, pos = await monitor(['armory'])
    await hand.click(pos, delay=2)
    pos_types = [
        (820, 190),
        (820, 270),
        (820, 350),
        (820, 440),
    ]
    # 不能每次都薅同一只羊
    len_num = len(pos_types)
    idx = random.choice(range(len_num))
    for i in range(len_num):
        pos_type = pos_types[(idx + i) % len_num]
        await hand.click(pos_type)
        pos_list = await find_all_pos(['arms'], threshold=0.97)
        if pos_list:
            pos_list = sorted(pos_list, key=itemgetter(1, 0))
            pos = pos_list[0]
            pos = (pos[0] - 30, pos[1] + 30)
            await hand.click(pos)
            pos_quantity = (220, 330)
            pos_ok = (810, 480)
            pos_forging = (250, 450)
            await hand.click(pos_quantity)
            await hand.tap_key('2')
            await hand.click(pos_ok)
            await hand.click(pos_forging)
            break
    else:
        logger.info("There are not enough equipment for synthesis.")

    await goto_main_interface()
    return


async def market():
    await move_to_left_down()
    _, pos = await monitor(['market'])
    await hand.click(pos, delay=2)

    pos_get_gold = (410, 50)
    await hand.click(pos_get_gold, cheat=False)
    for _ in range(2):
        try:
            _, pos = await monitor(['get_for_free', 'get_for_free1', 'get_for_free2'], threshold=0.92, timeout=2)
            await hand.click(pos)
            name, pos = await monitor(['ok7', 'ok8', 'ok9'])
            await hand.click(pos)
        except FindTimeout:
            break
    await hand.tap_key(player_hand.k.escape_key, delay=1)

    pics3 = ['hero_badge', 'task_ticket']
    pics1 = ['hero_badge', 'task_ticket',
             'soda_water1', 'soda_water2', 'soda_water3']
    offset1 = 40
    pics2 = ['hero_shard_3_1', 'hero_shard_3_2', 'hero_shard_3_3',
             'hero_shard_3_4', 'hero_shard_4_1', 'hero_shard_4_2', 'hero_shard_4_3']
    offset2 = 10
    for _ in range(4):
        for pics, offset in [(pics1, offset1), (pics2, offset2)]:
            pos_list = await find_all_pos(pics, threshold=0.92)
            for pos in pos_list:
                pos = (pos[0], pos[1] + offset)
                await hand.click(pos)
                try:
                    _, pos = await monitor(['ok7', 'ok8', 'ok9'], timeout=2)
                    await hand.click(pos)
                    name, pos = await monitor(['ok7', 'ok8', 'ok9', 'lack_of_gold'])
                except FindTimeout:
                    continue  # 有些东西被购买了，还是能匹配到
                if name in ['ok7', 'ok8', 'ok9']:
                    await hand.click(pos)
                else:
                    logger.debug('lack of gold')
                    return await goto_main_interface()
        try:
            name, pos = await monitor(['refresh', 'refresh1', 'refresh2'], threshold=0.92, timeout=2)
            # name, pos = await monitor(['refresh', 'refresh1', 'refresh2', 'refresh3'], threshold=0.92, timeout=2)
            await hand.click(pos)
            # if name == 'refresh3':
            #     _, pos = await monitor(['ok8'])
            #     await hand.click(pos)
        except FindTimeout:
            return await goto_main_interface()
            

async def fight_arena():
    _, pos = await monitor(['start_fight'])
    await hand.click(pos, delay=3)
    # 25级以下无法加速，60以下无法快进
    for _ in range(3):
        pos_list = await find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
        if pos_list:
            for pos in pos_list:
                await hand.click(pos)
            break
        await asyncio.sleep(1)

    _, pos = await monitor(['card'], timeout=180)
    await hand.click(pos)
    await hand.click(pos)
    fight_res, pos = await monitor(['win', 'lose'])
    pos_ok = (430, 430)
    await hand.click(pos_ok, delay=3)
    return fight_res

async def arena():
    await move_to_center()
    _, pos = await monitor(['arena'])
    await hand.click(pos)
    
    _, pos = await monitor(['enter'])
    await hand.click(pos)

    for _ in range(3):
        _, pos = await monitor(['fight7'])
        await hand.click(pos)
        _, pos = await monitor(['fight8'], filter_func=filter_bottom)
        await hand.click(pos)
        res = await fight_arena()
        if res != 'win':
            logger.debug('Fight lose.')
            break
    
    await goto_main_interface()
    




async def do_play():
    funcs = [
        # collect_mail,
        # friends_interaction,
        # community_assistant,
        # instance_challenge,
        # guild,
        # exciting_activities,
        # jedi_space,
        # survival_home,
        invite_heroes,
        # armory,
        # market,
        # arena,

        # level_battle,
        # tower_battle,
    ]

    count = 0
    for func in funcs:
        logger.info("Start to run: " + func.__name__)
        try:
            await func()
        except FindTimeout as e:
            count += 1
            save_timeout_pic(str(e))
            await goto_main_interface()
            if count > 3:
                logger.error('Timeout too many times, so exit')
                break


async def auto_play():
    await asyncio.sleep(2)
    await do_play()


if __name__ == '__main__':
    start_time = time.time()
    manager = Manager()
    find_queue = manager.Queue()
    found_queue = manager.Queue()
    screen_dict = manager.dict()

    # Register the signal handlers
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)

    pool = Pool(4, init_worker)
    for _ in range(4):
        pool.apply_async(eye_woker, args=(
            find_queue, screen_dict, found_queue))

    # 创建协程
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(auto_play())
    except KeyboardInterrupt:
        logger.info("user canceled.")
    except ServiceExit:
        logger.info('user stop, exiting main program')
    except FindTimeout:
        logger.info('FindTimeout')
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        pool.terminate()
        pool.join()
        while not find_queue.empty():
            _ = find_queue.get()
        while not found_queue.empty():
            _ = find_queue.get()
        print('finally')
        end_time = time.time()
        print('Cost time:', end_time - start_time)
        # for p in workers:
        #     find_queue.put('STOP')
        #     p.join()
        # find_queue.close()
        # found_queue.close()


# TODO  要监控上一个标志，防止只点击一次没反应
# TODO  await asyncio.sleep(10) 的时候，ctrl+C 无法立即结束程序
# TODO  用回调可能可以增加性能
# TODO  每个函数写的时候，就要考虑所有情况，不要都在测试的时候发现, 就该
#       要养成严谨的编程习惯
# TODO  截图时，隐藏鼠标
# DONE  将fight抽取出来，作为公共功能

# TODO ctrl C 还是会报错

# TODO 将各个任务函数改成类
# TODO 建立数据库，配置文件，为每个角色建立基本信息
#      比如等级、今日任务是否完成 ……

# TODO goto_main 超时的话，就应该重启游戏

# TODO 不要过早优化代码，类似的功能，使用不同的函数实现，
# 后期所有功能都ok之后，再来抽取共性。

# v2 功能新增
# - 抽象出战斗逻辑

# 很多图需要重新截图，因为窗口大小变了
# 原来是 910 * 520 现在是 960 * 550
# => 着是多开器搞的鬼，开2个窗口是 960 * 550， 3个则是910 * 520
# 记录下窗口大小参数，不确定的地方采用图像识别，别的一律用坐标

# TODO timeout 就应该直接退出，方便debug

# TODO 监控boos，设别率太低

# TODO 英雄列表已满

# TODO 页面不打debug，只打印info，每个任务，skip原因

# TODO 解决图像识别率达不够高，导致bug的问题


# add one line