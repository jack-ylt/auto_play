import time
import os
import asyncio
import shutil
import datetime
import re
import random
import math
from operator import itemgetter
from collections import namedtuple
from cv2 import threshold
from playsound import playsound
import math

from lib.ui_data import SCREEN_DICT, OK_BUTTONS, GOOD_TASKS, CLOSE_BUTTONS
from lib.player import Player, FindTimeout

# from ui_data import SCREEN_DICT
# from player import Player, FindTimeout

import logging
logger = logging.getLogger(__name__)


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


def save_timeout_pic(msg):
    # f"{self.window_name}: monitor {names} timeout. ({timeout} s)"
    screen_pic = SCREEN_DICT['screen']
    timestr = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    window_name = re.search(r'(\w+):', msg).group(1)
    monitor_items = re.search(r'\[.+\]', msg).group()
    log_pic = os.path.join(
        './timeout_pics', f"{timestr}_{window_name}_{monitor_items}.jpg")
    shutil.copyfile(screen_pic, log_pic)
    logger.info(f"save_timeout_pic: {monitor_items}")
    playsound('./sounds/error.mp3')


class PlayException(Exception):
    pass


class AutoPlay(object):
    def __init__(self, player):
        self.player = player
        self.logger = self.player.logger

    #
    # public functions
    #
    async def _move_to_left_top(self):
        self.logger.debug('_move_to_left_top')
        p1 = (200, 300)
        p2 = (800, 400)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def _move_to_right_top(self):
        self.logger.debug('_move_to_right_top')
        p1 = (700, 200)
        p2 = (200, 400)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def _move_to_center(self):
        self.logger.debug('_move_to_center')
        await self._move_to_left_top()
        p1 = (500, 300)
        p2 = (200, 300)
        await self.player.drag(p1, p2)

    async def _move_to_left_down(self):
        self.logger.debug('_move_to_left_down')
        p1 = (200, 400)
        p2 = (700, 200)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def _close_ad(self, timeout=1):
        await asyncio.sleep(1)
        try:
            _, pos = await self.player.monitor(['close_btn1', 'close_btn2', 'close_btn3'], timeout=timeout)
            await self.player.click(pos)
        except FindTimeout:
            pass

    # async def in_main_interface(self):
    #     try:
    #         await self.player.monitor(['setting'], timeout=1)
    #         return True
    #     except FindTimeout:
    #         return False

    def save_operation_pics(self, msg):
        now = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        dir_name = msg.replace(', ', ',').replace(
            ':', '-').replace(' ', '-') + '_' + now
        dir = os.path.join('./timeout_pics', dir_name)
        os.makedirs(dir)
        self.player.save_operation_pics(dir)

    async def goto_main_interface(self):
        success = await self.player.go_back_to('setting')
        if not success:
            msg = "[goto main interface failed]"
            self.save_operation_pics(msg)
            self.logger.error(msg, exc_info=True)
            raise Exception(msg)

    async def _equip_team(self):
        x = 120
        y = 450
        dx = 65
        pos_list = [(x, y)]
        for _ in range(5):
            x += dx
            pos_list.append((x, y))

        await self.player.multi_click(pos_list)


    async def _do_fight(self):
        name_list = ['fast_forward1', 'go_last', 'win', 'lose']
        while True:
            name = await self.player.find_then_click(name_list, threshold=0.9, timeout=240)
            if name in ['win', 'lose']:
                return name
            else:
                name_list = name_list[name_list.index(name) + 1:]

    async def _fight(self):
        """do fight, return win or lose"""
        await self.player.find_then_click(['start_fight', 'fight1'])
        await asyncio.sleep(10)
        res = await self._do_fight()
        pos_ok = (430, 430)
        await self.player.click(pos_ok, delay=4)
        return res

    #
    # level_battle
    #
    async def _nextlevel_to_fight(self, pos):
        """go from next_level to fight"""
        await self.player.click(pos)
        try:
            name, pos = await self.player.monitor(['search', 'level_map'])
        except FindTimeout:
            self.logger.debug("reach the max level, so return")
            return False
            # 打到当前等级的关卡上限了
        if name == 'search':
            await self.player.click(pos)
            await asyncio.sleep(10)    # TODO vip no need 10s
        else:
            await asyncio.sleep(5)
            pos_list = await self.player.find_all_pos(['point', 'point3'], threshold=0.9)
            pos = filter_rightmost(pos_list)
            # 往右偏移一点，刚好能点击进入到下一个大关卡
            await self.player.click((pos[0] + 50, pos[1]))
            await self.player.find_then_click(['ok1'])
            await asyncio.sleep(10)

        await self.player.find_then_click(['fight'])
        return True

    async def _passed_to_fight(self):
        """go from already_passed to fight"""
        try:
            name, pos = await self.player.monitor(['next_level2', 'next_level3'], threshold=0.85)
        except FindTimeout:
            return False
        await self.player.click(pos, cheat=False)
        name, pos = await self.player.monitor(['search', 'level_low'])
        if name == 'level_low':
            self.logger.debug("reach the max level, so return")
            return False
        else:
            await self.player.click(pos)
            await asyncio.sleep(10)
            await self.player.find_then_click(['fight'])
            return True

    async def _hand_upgraded(self):
        await asyncio.sleep(5)

        try:
            _, pos = await self.player.monitor(['map_unlocked'])
        except FindTimeout:
            pass
        else:
            await self.player.click(pos)
            await asyncio.sleep(5)

            await self._move_to_center()
            _, pos = await self.player.monitor(['level_battle'])
            await self.player.click(pos, delay=3)
        finally:
            name, pos = await self.player.monitor(['next_level1', 'already_passed', 'fight'])

        return (name, pos)

    async def level_battle(self):
        """关卡战斗"""
        await self._move_to_center()

        await self.player.find_then_click(['level_battle'])
        await asyncio.sleep(3)

        await self.player.monitor(['ranking_icon'])
        await self._close_ad()

        pos_box = (750, 470)
        await self.player.click(pos_box)
        await self.player.find_then_click(['receive'], raise_exception=False)

        name, pos = await self.player.monitor(['upgraded', 'next_level1', 'already_passed', 'fight'])
        if name == 'upgraded':
            name, pos = await self._hand_upgraded()

        if name == 'next_level1':
            success = await self._nextlevel_to_fight(pos)
            if not success:
                return
        elif name == 'already_passed':
            success = await self._passed_to_fight()
            if not success:
                return
        else:    # fight
            await self.player.click(pos)

        while True:
            res = await self._fight()

            if res == 'lose':
                self.logger.debug('Fight fail, so exit')
                # 打不过，就需要升级英雄，更新装备了
                return

            try:
                name, pos = await self.player.monitor(['upgraded', 'next_level1'])
            except FindTimeout:
                # 打到最新关了
                return

            if name == 'upgraded':
                name, pos = await self._hand_upgraded()

            success = await self._nextlevel_to_fight(pos)
            if not success:
                return

    #
    # tower_battle
    #
    async def tower_battle(self):
        await asyncio.sleep(1)
        await self._move_to_right_top()
        await self.player.find_then_click(['warriors_tower'])
        await self.player.monitor(['go_back', 'go_back1', 'go_back2'])

        pos_list = [
            (200, 360),
            (420, 360),
            (650, 360),
        ]
        await self.player.multi_click(pos_list)

        while True:
            await self.player.find_then_click('challenge')
            await self.player.find_then_click('start_fight')
            while True:
                name = await self.player.find_then_click(['next_level4', 'ok', 'fast_forward1', 'go_last'], timeout=60)
                if name == 'next_level4':
                    break
                if name == 'ok':
                    # 打不过，就需要升级英雄，更新装备了
                    return False

    #
    # collect_mail
    #
    async def collect_mail(self):
        try:
            _, pos = await self.player.monitor(['mail'], threshold=0.97, timeout=1)
        except FindTimeout:
            self.logger.debug("There is no new mail.")
            return
        await self.player.click(pos)
        await self.player.find_then_click(['one_click_collection'])

    #
    # friends_interaction
    #
    async def _fight_friend(self, max_try=5):
        max_try = max_try
        count = 0
        pos_ok_win = (430, 430)
        pos_ok_lose = (340, 430)
        pos_next = (530, 430)
        _, pos_fight = await self.player.monitor(['start_fight'])

        try:
            await self.player.monitor(['skip_fight'], threshold=0.9, timeout=1)
            skip_fight = True
        except FindTimeout:
            skip_fight = False

        await self.player.click(pos_fight)

        while True:
            count += 1
            if not skip_fight:
                await asyncio.sleep(3)
                # 25级以下无法加速，60以下无法快进
                for _ in range(3):
                    pos_list = await self.player.find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
                    if pos_list:
                        for pos in pos_list:
                            await self.player.click(pos)
                        break
                    await asyncio.sleep(1)
            _, pos = await self.player.monitor(['card'], timeout=240)
            await self.player.click(pos)    # 卡片点两次，才会消失
            await self.player.click(pos)
            fight_res, pos = await self.player.monitor(['win', 'lose'], threshold=0.9)
            if fight_res == 'win':
                await self.player.click(pos_ok_win)
                break
            else:
                if count < max_try:
                    await self.player.click(pos_next)
                else:
                    await self.player.click(pos_ok_lose)
                    break

        if not skip_fight:
            await asyncio.sleep(3)
        return fight_res

    async def friends_interaction(self):
        try:
            _, pos = await self.player.monitor(['friends'], threshold=0.95, timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            self.logger.debug(
                "There is no new interaction of friends.")
            return

        await self.player.find_then_click(['receive_and_send'])

        try:
            _, pos = await self.player.monitor(['friends_help'], threshold=0.9, timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            self.logger.debug(
                "There is no friend need help.")
            return

        while True:
            try:
                _, (x, y) = await self.player.monitor(['search1'], threshold=0.9, timeout=1)
                pos = (x, y + 15)
                await self.player.click(pos)
            except FindTimeout:
                self.logger.debug(
                    "There is no more boss.")
                return

            name, pos = await self.player.monitor(['fight2', 'ok', 'ok9'])
            if name in ['ok', 'ok9']:
                return

            await self.player.click(pos)
            _, pos = await self.player.monitor(['fight3'])
            await self.player.click(pos)

            res = await self._fight_friend()
            if res != 'win':
                self.logger.debug(" Can't win the boos")
                return

    #
    # community_assistant
    #
    async def community_assistant(self):
        await self.player.find_then_click(['community_assistant'])

        try:
            _, pos = await self.player.monitor(['guess_ring'], threshold=0.97, timeout=2)
        except FindTimeout:
            self.logger.debug(
                "Fress guess had been used up.")
            return

        pos_lsts = [(50, 240), (50, 330), (50, 400)]
        for pos in pos_lsts:
            try:
                await self.player.monitor(['level_60'], threshold=0.95, timeout=1)
                await self.player.click(pos, delay=2)
            except FindTimeout:
                break

        try:
            await self.player.find_then_click(['guess_ring'], threshold=0.97, timeout=1)
        except FindTimeout:
            self.logger.info(
                "need buy the assistant first.")
            return

        while True:
            try:
                name = await self.player.find_then_click(['close', 'cup'], threshold=0.9)
                if name == "close":
                    break
                name = await self.player.find_then_click(['close', 'next_game'])
                if name == "close":
                    break
            except FindTimeout:
                break

        await self.player.go_back_to('gift')

        try:
            await self.player.find_then_click(['have_a_drink'], timeout=2)
        except FindTimeout:
            pass

        try:
            _, pos = await self.player.monitor(['gift'])
            pos_recive_all = (800, 255)
            await self.player.click(pos_recive_all)
            await self.player.click(pos)
        except FindTimeout:
            return

        pos_select_gift = (70, 450)
        pos_send_gift = (810, 450)
        while True:
            await self.player.click(pos_select_gift, delay=0.2)
            await self.player.click(pos_send_gift)
            try:
                name = await self.player.find_then_click(['start_turntable', 'close_btn1'], timeout=1)
                if name == 'close_btn1':
                    # 点击中间，让go_back露出来
                    await  self.player.click((40, 200))
                    return
                else:
                    await asyncio.sleep(5)
            except FindTimeout:
                pass

    #
    # instance_challenge
    #

    async def _fight_challenge(self):
        # 25级以下无法加速，60以下无法快进
        for _ in range(3):
            pos_list = await self.player.find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
            if pos_list:
                for pos in pos_list:
                    await self.player.click(pos)
                break
            await asyncio.sleep(1)

        fight_res, pos = await self.player.monitor(['win', 'lose'], threshold=0.9, timeout=240)
        return fight_res

    async def instance_challenge(self):
        try:
            _, pos = await self.player.monitor(['Instance_challenge'], threshold=0.97, timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            self.logger.debug("No new challenge.")
            return

        # challenge_list = await self.player.find_all_pos(['challenge2'], threshold=0.93)
        challenge_list = await self.player.find_all_pos('red_point')
        pos_ok = (430, 430)
        pos_next = (530, 430)
        for pos in challenge_list:
            pos = (pos[0] - 50, pos[1] + 20)
            await self.player.click(pos)
            pos_list = await self.player.find_all_pos(['challenge3', 'mop_up', 'mop_up1'])
            if not pos_list:
                msg = "no found any of ['challenge3', 'mop_up', 'mop_up1']"
                self.logger.warning(msg)
                self.save_operation_pics(msg)
                await self.player.go_back_to('challenge_dungeon')
                continue
            pos = filter_bottom(pos_list)
            await self.player.click(pos)
            name, pos = await self.player.monitor(['start_fight', 'next_game1'])

            if name == 'start_fight':
                await self.player.click(pos)
                await asyncio.sleep(3)
                res = await self._fight_challenge()
                if res != 'win':
                    self.logger.debug("Fight lose")
                else:
                    await self.player.click(pos_next, delay=3)
                    await self._fight_challenge()
                await self.player.click(pos_ok, delay=3)
            else:
                await self.player.click(pos_next)
                await self.player.click(pos_ok)

            await self.player.go_back_to('challenge_dungeon')

    #
    # guild
    #

    async def _fight_guild(self):
        _, pos = await self.player.monitor(['start_fight'])
        await self.player.click(pos, delay=3)
        
        await self.player.monitor('message')
        pos_go_list = (835, 56)
        await self.player.click(pos_go_list)

        _, pos = await self.player.find_then_click('ok')

    async def guild(self):
        try:
            _, pos = await self.player.monitor(['guild'], threshold=0.97, timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            self.logger.debug("No new guild event.")
            return

        _, pos_guild_territory = await self.player.monitor('guild_territory')
        await self.player.find_then_click('sign_in', threshold=0.95, timeout=1, raise_exception=False)
        await self.player.click(pos_guild_territory)

        # guild_instance
        _, pos = await self.player.monitor(['guild_instance'])
        await self.player.click(pos)
        try:
            name, pos = await self.player.monitor(['boss_card', 'boss_card1'], threshold=0.92, timeout=3)
            # 匹配的是卡片边缘，而需要点击的是中间位置
            if name == 'boss_card':
                pos = (pos[0], pos[1]+50)
            else:
                pos = (pos[0], pos[1]-50)
            await self.player.click(pos)

            _, (x, y) = await self.player.monitor(['fight4', 'fight5'], threshold=0.84, timeout=1)
            pos = (x-50, y-50)
            await self.player.click(pos)
            await self._fight_guild()
        except FindTimeout:
            pass

        # guild_factory
        await self.player.go_back_to('guild_factory')

        await asyncio.sleep(1)    # 防止点太快
        await self.player.find_then_click('guild_factory', timeout=1)

        try:
            for i in range(2):
                _, pos = await self.player.monitor(['order_completed', 'ok1'], timeout=3)
                await self.player.click(pos)
        except FindTimeout:
            pass

        _, pos = await self.player.monitor(['get_order'])
        await self.player.click(pos)
        pos_start_all = (510, 140)
        await self.player.click(pos_start_all)
        # pos_list = await self.player.find_all_pos(['start_order'])
        # for pos in pos_list:
        #     await self.player.click(pos)
        # await self._move_to_right_top()
        # pos_list = await self.player.find_all_pos(['start_order'])
        # for pos in pos_list:
        #     await self.player.click(pos)

        # Donate
        pos_donate_home = (770, 270)
        await self.player.click(pos_donate_home)
        _, pos = await self.player.monitor(['donate'])
        await self.player.click(pos)
        try:
            _, pos = await self.player.monitor(['ok5'], timeout=1)
            await self.player.click(pos)
        except:
            pass

        # open boxes
        pos_list = await self.player.find_all_pos(['box1'], threshold=0.9)
        for p in sorted(pos_list):
            await self.player.click(p)
            _, pos = await self.player.monitor(['ok4', 'ok13'], timeout=2)
            await self.player.click(pos)

    #
    # exciting_activities
    #

    async def exciting_activities(self):
        pos_exciting_activities = (740, 70)
        await self.player.click(pos_exciting_activities)
        pos_sign_in = (700, 430)
        for _ in range(2):
            await self.player.click(pos_sign_in)

    #
    # jedi_space
    #

    async def jedi_space(self):
        await self._move_to_left_top()
        _, pos = await self.player.monitor(['jedi_space'])
        await self.player.click(pos)

        pos_challenge = (430, 450)
        await self.player.click(pos_challenge)
        pos_mop_up = (650, 150)
        await self.player.click(pos_mop_up)

        try:
            await self.player.find_then_click(['max'], timeout=1, cheat=False)
        except FindTimeout:
            return

        pos_ok1 = (430, 415)
        await self.player.click(pos_ok1)

    #
    # 生存家园 survival_home
    #

    async def _drag(self, d):
        pos1 = (55, 300)
        pos2 = (55, 400)
        if d == 'up':
            await self.player.drag(pos2, pos1, speed=0.02)
        elif d == 'down':
            await self.player.drag(pos1, pos2, speed=0.02)
        await asyncio.sleep(1)

    async def _get_total_floors(self):
        await self.player.find_then_click('switch_map')
        await asyncio.sleep(1)
        
        await self._drag('up')
        map_list = await self.player.find_all_pos('locked_field')
        locked_field = len(map_list)
        if locked_field == 0:
            await self.player.find_then_click('switch_map')
            return 7

        await self._drag('down')
        map_list = await self.player.find_all_pos('locked_field')
        locked_field += len(map_list)
        
        if locked_field >= 5:
            # 第四层没有解锁的话，会被重复统计
            floors = 7 - locked_field + 1
        else:
            floors = 7 - locked_field

        await self._drag('up')
        await self.player.find_then_click('switch_map')
        return floors


    async def _goto_floor(self, i, pre=None):
        if pre is None:
            # 第一次进来，刚好就在最高的那一层
            return i

        pos_map = {
            1: (50, 288),
            2: (50, 321),
            3: (50, 356),
            4: (50, 306),
            5: (50, 342),
            6: (50, 375),
            7: (50, 409)
        }

        await self.player.find_then_click('switch_map')

        if pre >= 4 and i <= 3:
            # await self.player.scroll(5, pos=(50, 350))
            await self._drag('down')

        await asyncio.sleep(0.2)
        await self.player.click(pos_map[i])
        await self.player.find_then_click('switch_map')

        return i

    async def _swip_to(self, direction, stop=False):
        left_top = (150, 150)
        top = (400, 150)
        right_top = (700, 150)
        left = (150, 270)
        right = (700, 270)
        left_down = (150, 370)
        down = (400, 370)
        right_down = (700, 370)

        swip_map = {
            'left_top': (left_top, right_down),
            'left_down': (left_down, right_top),
            'right_down': (right_down, left_top),
            'right_top': (right_top, left_down),
            'top': (top, down),
            'down': (down, top),
            'left': (left, right),
            'right': (right, left),
        }

        self.logger.debug('swipe_to {direction}')
        p1, p2 = swip_map[direction]
        await self.player.drag(p1, p2, speed=0.02, stop=stop)

    async def _collect_box(self):
        boxes = await self.player.find_all_pos('box')
        for p in boxes:
            await self.player.click(p, cheat=False, delay=0.2)

    async def _fight_home_boos(self, win_count, max_fight, max_try=1):
        can_win = True

        while True:
            try:
                name, p = await self.player.monitor(['boss', 'boss1', 'boss2'], timeout=1)
            except FindTimeout:
                return win_count, can_win

            # 点boos中心，因为某些位置点了无效
            p = (p[0] + 40, p[1] - 40)
            if not self._can_click(p):
                # 点不了，就返回，等移动了，可能就能点了
                return win_count, can_win

            await self.player.click(p, cheat=False)
            win = await self._fight_home(max_try=max_try)
            if win:
                win_count += 1
                if win_count >= max_fight:
                    return win_count, can_win
            else:
                self.logger.warning("Fight lose.")
                can_win = False
                return win_count, can_win

    def _can_click(self, boss_pos):
        """确保在可点击区域"""
        x, y = boss_pos
        if x < 30 or x > 830:
            return False
        if y < 90 or y > 490:
            return False
        if x < 100 and y > 410:
            return False
        if x > 690 and y > 400:
            return False
        return True

    async def _fight_home(self, max_try=2):
        pos_ok_win = (430, 430)
        pos_ok_lose = (340, 430)
        pos_next = (530, 430)
        count = 1

        await self.player.find_then_click('fight6')
        await self.player.find_then_click('start_fight')

        while True:
            try:
                await self.player.find_then_click(['win', 'lose', 'go_last'], threshold=0.9)
            except FindTimeout:
                pos_go_last = (836, 57)
                await self.player.click(pos_go_last)

            fight_res, pos = await self.player.monitor(['win', 'lose'], threshold=0.9, timeout=240)
            if fight_res == 'win':
                await self.player.click(pos_ok_win)
                # await self.player.monitor(['go_back', 'go_back1', 'go_back2'])
                return True
            else:
                if count < max_try:
                    await self.player.click(pos_next)
                    count += 1
                else:
                    await self.player.click(pos_ok_lose)
                    # await self.player.monitor(['go_back', 'go_back1', 'go_back2'])
                    return False

    async def survival_home(self):
        await self._move_to_left_top()
        await self.player.find_then_click('survival_home')
        try:
            _, pos = await self.player.monitor('resources', timeout=3)
            await asyncio.sleep(3)    # 点太快，可能卡住
            await self.player.click(pos)
        except FindTimeout:
            await asyncio.sleep(3)    # 点太快，可能卡住

        pos_fight = (830, 490)
        await self.player.click(pos_fight)
        await asyncio.sleep(3)
        total_floors = await self._get_total_floors()

        max_fight = 4
        win_count = 0
        pre_floor = None
        for i in range(total_floors, 0, -1):
            print(i)
            pre_floor = await self._goto_floor(i, pre_floor)
            await asyncio.sleep(1)    # 点太快，可能卡住
            can_win = True
            for d in [None, 'left_top', 'left_down', 'right_down', 'right_top']:
                if d:
                    await self._swip_to(d)
                await self._collect_box()
                if can_win and win_count < max_fight:
                    win_count, can_win = await self._fight_home_boos(win_count, max_fight, max_try=1)

    #
    # invite_heroes
    #

    async def _dismiss_heroes(self):
        _, pos = await self.player.monitor(['dismiss_hero'])
        await self.player.click(pos, delay=2)
        pos_1 = (520, 425)
        pos_2 = (580, 425)
        pos_put_into = (150, 440)
        pos_dismiss = (320, 440)

        await self.player.click(pos_1)
        await self.player.click(pos_put_into)
        await self.player.click(pos_dismiss)
        try:
            _, pos = await self.player.monitor(['receive1'], timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            pass

        await self.player.click(pos_2)
        await self.player.click(pos_put_into)
        await self.player.click(pos_dismiss)
        try:
            _, pos = await self.player.monitor(['receive1'], timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            pass

    async def invite_heroes(self):
        await self._move_to_left_down()
        _, pos = await self.player.monitor(['invite_hero'])
        await self.player.click(pos)
        await self.player.monitor('beer')
        pos_list = await self.player.find_all_pos(['invite_free', 'invite_soda', 'invite_beer'])

        for p in pos_list:
            await self.player.click(p)
            name, pos = await self.player.monitor(['ok9', 'ok10', 'close'])
            await self.player.click(pos)
            # 如果英雄列表满了，就遣散英雄
            if name == 'close':
                pos_list.append(p)    # ，没邀请成功，就再试一次

                await self._dismiss_heroes()
                _, pos = await self.player.monitor(['invite_hero'])
                await self.player.click(pos, delay=2)

    #
    # armory
    #

    async def armory(self):
        await self._move_to_right_top()
        _, pos = await self.player.monitor(['armory'])
        await self.player.click(pos, delay=2)
        pos_types = [
            (820, 190),
            (820, 270),
            (820, 350),
            (820, 440),
        ]
        pos_quantity = (220, 330)
        pos_enter = (810, 480)
        pos_forging = (250, 450)
        # 不能每次都薅同一只羊
        len_num = len(pos_types)
        idx = random.choice(range(len_num))

        count = 0
        for i in range(len_num):
            pos_type = pos_types[(idx + i) % len_num]
            await self.player.click(pos_type)
            # 匹配上所有点，但排除右边pos_types的那些点
            pos_list = await self.player.find_all_pos(['arms'], threshold=0.8)
            pos_list = list(
                filter(lambda x: x[0] < 800 or 0 < x[0] - 910 < 800, pos_list))
            if pos_list:
                await self.player.information_input(pos_quantity, '3')
                await self.player.click(pos_enter)
                try:
                    await self.player.monitor('number_3', threshold=0.9, timeout=1)
                    count += 3
                except:
                    count += 1
                await self.player.click(pos_forging)

                if count >= 3:
                    return
        else:
            self.logger.info(
                "There are not enough equipment for synthesis.")

    #
    # market
    #

    async def market(self):
        await self._move_to_left_down()
        await self.player.find_then_click('market')
        await self.player.monitor(['gold', 'diamond'])
        await self._receive_survival_reward()

        fresh_btn = (690, 135)
        for i in range(4):
            await self._buy_goods()
            await self.player.click(fresh_btn)
            try:
                await self.player.find_then_click('cancle', timeout=1)
                break
            except FindTimeout:
                pass

        await self._buy_premium_goods()

    async def _receive_survival_reward(self):
        pos_plus = (411, 54)
        await self.player.click(pos_plus, cheat=False)
        pos_receive = (350, 390)
        for i in range(2):
            await self.player.click(pos_receive)
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=1)
            except FindTimeout:
                break
        await self.player.go_back_to('premium')

    async def _buy_goods(self):
        nice_goods = ['task_ticket', 'hero_badge', 'arena_tickets',
                      'soda_water', 'hero_blue', 'hero_green', 'hero_light_blue', 'hero_red']
        list1 = await self.player.find_all_pos('gold')
        list2 = await self.player.find_all_pos(nice_goods)
        pos_list = self._merge_pos_list(list1, list2, dx=50, dy=100)
        for pos in pos_list:
            if await self.player.is_disabled_button(pos):
                continue
            pos = (pos[0] + 30, pos[1])
            await self.player.click(pos)
            await self.player.find_then_click(OK_BUTTONS)
            await self.player.find_then_click(OK_BUTTONS)

    async def _buy_premium_goods(self):
        await self.player.find_then_click('premium')
        try:
            await self.player.find_then_click('go_page_2', timeout=2)
        except FindTimeout:
            self.logger.debug("can't buy premium goods, for low level")
            return
        list1 = await self.player.find_all_pos('gold1')
        list2 = await self.player.find_all_pos('arena_tickets')
        pos_list = self._merge_pos_list(list1, list2, dx=50, dy=100)
        for pos in pos_list:
            if await self.player.is_disabled_button(pos):
                continue
            pos = (pos[0] + 30, pos[1])
            await self.player.click(pos)
            await self.player.find_then_click(OK_BUTTONS)
            await self.player.find_then_click(OK_BUTTONS)

 

    #
    # arena
    #

    async def _fight_arena(self):
        _, pos_fight = await self.player.monitor(['start_fight'])

        try:
            await self.player.monitor(['skip_fight'], threshold=0.9, timeout=1)
            skip_fight = True
        except FindTimeout:
            skip_fight = False

        await self.player.click(pos_fight)

        if not skip_fight:
            # 25级以下无法加速，60以下无法快进
            for _ in range(3):
                pos_list = await self.player.find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
                if pos_list:
                    for pos in pos_list:
                        await self.player.click(pos)
                    break
                await asyncio.sleep(1)

        _, pos = await self.player.monitor(['card'], timeout=240)
        await self.player.click(pos)
        await self.player.click(pos)
        fight_res, pos = await self.player.monitor(['win', 'lose'], threshold=0.9)
        pos_ok = (430, 430)
        await self.player.click(pos_ok)
        if not skip_fight:
            await asyncio.sleep(4)

        return fight_res

    async def _swip_up(self):
        self.logger.debug('swipe_up')
        p1 = (300, 400)
        p2 = (300, 150)
        await self.player.drag(p1, p2, speed=0.02)
        await asyncio.sleep(1)

    async def arena(self):
        await self._move_to_center()
        _, pos = await self.player.monitor(['arena'])
        await self.player.click(pos)

        _, pos = await self.player.monitor(['enter'])
        await self.player.click(pos, delay=2)

        pos_refresh = (660, 170)
        for i in range(7):
            _, pos = await self.player.monitor(['fight7'])
            await self.player.click(pos)
            if i > 4:
                await self.player.click(pos_refresh)
            _, pos = await self.player.monitor(['fight8'], filter_func=filter_bottom)
            await self.player.click(pos)
            res = await self._fight_arena()
            if res != 'win':
                self.logger.debug('Fight lose.')
                break

        try:
            _, pos = await self.player.monitor(['reward'], timeout=1, threshold=0.9)
            await self.player.click(pos)

            pos_list = await self.player.find_all_pos(['receive2'], threshold=0.9)
            if not pos_list:
                await self._swip_up()
                pos_list = await self.player.find_all_pos(['receive2'], threshold=0.9)

            for pos in sorted(pos_list, key=lambda x: x[1]):
                await self.player.click(pos)
                try:
                    _, pos = await self.player.monitor(['ok12'], timeout=1)
                    await self.player.click(pos)
                except FindTimeout:
                    break
        except FindTimeout:
            pass

    async def arena_champion(self, min_score=50):

        await self.player.find_then_click('arena')
        await self.player.find_then_click('champion')
        await self.player.find_then_click('enter')

        # 第一次进入，需要设置上阵英雄
        try:
            await self.player.find_then_click(CLOSE_BUTTONS, timeout=2)
            await self.player.find_then_click('save')
        except FindTimeout:
            pass

        page = 4
        idx = 1
        score = 0
        win = 0
        lose = 0
        pos_refresh = (660, 170)
        pos_fight = (700, 340)
        pos_ok = (440, 430)
        pos_fights = [
            (650, 250),
            (650, 330),
            (650, 415),
        ]

        while score < min_score:
            await self.player.monitor('fight7')
            await asyncio.sleep(1)
            # 如果没有跳过战斗，按钮有个从下往上的动画
            await self.player.find_then_click('fight7')
            await self.player.monitor('refresh_green')
            for _ in range(page):
                await self.player.click(pos_refresh, delay=0.3)
            await self.player.click(pos_fights[idx])
            await self.player.find_then_click(['fight_green'])
            for _ in range(10):
                name = await self.player.find_then_click(['card', 'ok12', 'next', 'go_last'])
                if name == 'card':
                    await self.player.click(pos_ok)
                    name = await self.player.find_then_click(['win', 'lose'], threshold=0.9)
                    if name == 'win':
                        score += 2
                        win += 1
                    else:
                        score += 1
                        lose += 1
                        idx += 1
                        if idx > 3:
                            idx = 1
                            page += 1
                    break
            await self.player.click(pos_ok)

        self.logger.info(f"win: {win}, lose: {lose}, score: {score}")

    #
    # brave_instance
    #

    async def brave_instance(self):
        """勇者副本"""
        await self._move_to_right_top()
        await self.player.find_then_click('brave_instance')
        if not await self._goto_curr_level():
            return 

        await self.player.find_then_click('challenge4')
        try:
            _, _ = await self.player.monitor('team_empty', timeout=2)
            await self._equip_team()
        except FindTimeout:
            pass

        while True:
            await self.player.find_then_click('start_fight')
            result = await self._fight_brave()
            if result == 'win':
                name = await self.player.find_then_click(['next_level4', 'ok'])
                if name == 'ok':
                    if not await self._goto_curr_level():
                        return
                await self.player.find_then_click('challenge4')
            else:
                await self.player.find_then_click(OK_BUTTONS)
                return


    async def _goto_curr_level(self):
        # try:
        #     _, (x, y) = await self.player.monitor(['current_level'], threshold=0.96, timeout=2)
        # except FindTimeout:
        #     await self._move_to_left_down()
        #     try:
        #         _, (x, y) = await self.player.monitor(['current_level'], threshold=0.96, timeout=2)
        #     except FindTimeout:
        #         await self._move_to_right_top()
        #         try:
        #              _, (x, y) = await self.player.monitor(['current_level'], threshold=0.96, timeout=2)
        #         except FindTimeout:
        #             self.logger.info("Can't found current level, the brave instance maybe finished.")
        #             return False
        
        await self.player.monitor('current_level', threshold=0.95)
        await asyncio.sleep(1)
        _, (x, y) = await self.player.monitor('current_level', threshold=0.95)
        await self.player.click((x, y + 40), cheat=False) 
        return True

    async def _fight_brave(self):
        for _ in range(5):
            name, pos = await self.player.monitor(['card', 'lose', 'go_last', 'fast_forward1'])
            if name == "card":
                await self.player.click(pos)
                await self.player.click(pos)
                return 'win'
            elif name in ['go_last', 'fast_forward1']:
                await self.player.click(pos)
            else:
                return 'lose'


    async def lucky_draw(self):
        await self.player.find_then_click(['lucky_draw'])
        await self.player.monitor('draw_once')
        await self.player.find_then_click(['draw_once'])
        await asyncio.sleep(8)
        await self.player.find_then_click(['draw_again'])

    async def task_board(self):
        # 如果有任务完成不了，就不要继续刷新任务了
        self.logger.info("Run task board")

        await self.player.find_then_click('task_board')
        try:
            # 确保界面刷新出来了
            await self.player.monitor(['receivable_task', 'delete_task', 'finish_btn'])
            # 看下是否有可领取的任务
            await self.player.monitor('receivable_task', timeout=1)
        except:
            self.logger.info("Skip, there is no receivable task")
            return

        await self._accept_task()
        await self._finish_all_tasks()

        # 最多刷新5次，如果钻石不够也能退出
        max_num = 5
        for i in range(max_num):
            await self.player.find_then_click('refresh4')
            await asyncio.sleep(2)
            try:
                await self.player.monitor('receivable_task', timeout=1)
            except FindTimeout:
                self.logger.info("All task had been accepted.")
                return
            await self._accept_task()

        self.logger.info(f"Reach max refresh times ({max_num})")

    async def _accept_task(self):
        one_key_to_battle = (350, 455)
        start_task = (520, 455)

        while True:
            list1 = await self.player.find_all_pos('receivable_task')
            list2 = await self.player.find_all_pos(GOOD_TASKS)
            pos_list = self._merge_pos_list(list1, list2, dx=10)
            for pos in pos_list:
                await self.player.click(pos)
                await self.player.monitor('close')
                await self.player.click(one_key_to_battle)
                await self.player.click(start_task)
                pos_list2 = await self.player.find_all_pos(['close', 'no_hero'])
                if pos_list2:
                    await self.player.click(start_task)
                    pos_list2 = await self.player.find_all_pos(['close', 'no_hero'])
                    if pos_list2:
                        raise PlayException("Lack of heroes to accept task")

            await self._swip_to('right', stop=True)

            try:
                await self.player.monitor('receivable_task', timeout=1)
            except FindTimeout:
                return

            try:
                await self.player.monitor(['finish_btn', 'unlock_more'], timeout=1)
                return
            except FindTimeout:
                pass

    def _merge_pos_list(self, btn_list, icon_list, dx=1000, dy=1000):
        def _is_close(p1, p2):
            x1, y1 = p1
            x2, y2 = p2
            # dy不试用绝对值，因为按钮一般在图标的下面
            if math.fabs(x1 - x2) <= dx and 0 <= y1 - y2 <= dy:
                return True
            return False

        merge_set = set()
        for p1 in btn_list:
            for p2 in icon_list:
                if _is_close(p1, p2):
                    merge_set.add(p1)
        merge_list = sorted(list(merge_set), key=lambda pos: pos[1])
        print(f"merge_list: {merge_list}")
        return merge_list

    async def _finish_all_tasks(self):
        await self.player.find_then_click('one_click_collection2')
        try:
            await self.player.find_then_click(OK_BUTTONS, timeout=2)
            await asyncio.sleep(2)
            await self.player.find_then_click(OK_BUTTONS, timeout=2)
            self.logger.info("All tasks had been finished.")
            return
        except FindTimeout:
            while True:
                await self._swip_to('right')
                try:
                    await self.player.monitor('unlock_more', timeout=2)
                    break
                except FindTimeout:
                    pass

            while True:
                try:
                    await self.player.find_then_click('finish_btn', timeout=1)
                    await self.player.find_then_click(OK_BUTTONS, timeout=1)
                    try:
                        # 高星任务会一次词确认
                        await self.player.find_then_click(OK_BUTTONS, timeout=1)
                    except FindTimeout:
                        pass
                except FindTimeout:
                    self.logger.info("All tasks had been finished.")
                    return

    async def vip_shop(self):
        pos_vip = (28, 135)
        await self.player.click(pos_vip, cheat=False)
        await self.player.monitor(['vip_shop'])
        try:
            await self.player.find_then_click(['receive_small'], timeout=1)
        except FindTimeout:
            pass

    async def maze(self):
        """Maze Treasure Hunt"""
        try:
            await self.player.find_then_click(['maze4'], timeout=1, cheat=False)
        except FindTimeout:
            self.logger.debug("There is no maze")
            return

        await self.player.monitor(['maze_text'])

        try:
            await self.player.find_then_click(['maze_daily_gift'], threshold=0.9, timeout=1)
        except FindTimeout:
            self.logger.debug("maze daily gift have been already recived.")
            return
        else:
            pos_recive = (700, 270)
            await self.player.click(pos_recive)

    async def hero_expedition(self):
        await self._move_to_right_top()
        await self.player.find_then_click(['hero_expedition'])
        try:
            await self.player.find_then_click(['production_workshop'])
            await self.player.find_then_click(['one_click_collection1'])
        except FindTimeout:
            self.logger.debug("hero_expedition need at least one 14 star hero.")
            while True:
                name, pos = await self.player.monitor(['go_back', 'go_back1', 'go_back2', 'setting'])
                if name == 'go_back' or name == 'go_back1' or name == 'go_back2':
                    await self.player.click(pos)
                else:
                    break

    async def _close_game(self):
        pos_recent_tasks = (885, 500)
        pos_clear_all = (630, 85)
        await self.player.click(pos_recent_tasks, delay=2)
        await self.player.click(pos_clear_all)

    async def login(self, account_pre, account_curr):
        # account_curr = Account(game_name, account, passwd, server)
        async def _login_server():
            """login via another server, if sucess, return True"""
            if not account_curr.server:
                return True

            _, pos = await self.player.monitor(['setting'])
            await self.player.click(pos)
            _, pos = await self.player.monitor(['server_icon'])
            await self.player.click(pos)
            await self.player.monitor(['server_ui'])
            pos = await self.player.find_text_pos(account_curr.server)
            if pos == (-1, -1):
                self.logger.warning(
                    f"login server faild: can't find the {account_curr.server}")
                return False

            await self.player.click(pos)
            try:
                await self.player.monitor(['changge_server_remind'], timeout=1)
                pos_ok = (500, 350)
                await self.player.click(pos_ok)
                await asyncio.sleep(3)
                await self.player.monitor(['setting'])
                await self._close_ad()
            except FindTimeout:
                # 想登陆的区，正好是当前的区，直接返回
                await self.player.go_back()

            return True

        async def _login_account():
            """login via another account, if sucess, return True"""
            _, pos = await self.player.monitor(['setting'])
            await self.player.click(pos)
            await self.player.monitor(['server_icon'])
            pos_exit = (650, 350)
            await self.player.click(pos_exit)
            pos_ok = (500, 350)
            await self.player.click(pos_ok)
            pos_start_game = (430, 490)
            await self.player.click(pos_start_game)
            name, pos = await self.player.monitor(['setting', 'game_91'])

            if name == 'game_91':
                pos_account = (370, 235)
                await self.player.information_input(
                    pos_account, account_curr.account)
                await asyncio.sleep(1)
                pos_passwd = (370, 290)
                await self.player.information_input(
                    pos_passwd, account_curr.passwd)
                pos_login = (430, 340)
                await self.player.click(pos_login)
                await asyncio.sleep(3)
                name, pos = await self.player.monitor(['setting', 'game_91'])
                if name == 'game_91':
                    return False
                else:
                    await self._close_ad()
                    return True
            else:
                # 只有一个用户，直接进入游戏
                await self._close_ad()
                return True

        async def _login_game():
            """start game and login, if sucess, return True"""
            _, pos = await self.player.monitor([account_curr.game_name])
            await asyncio.sleep(3)
            await self.player.double_click(pos)
            await asyncio.sleep(50)

            await self.player.monitor(['close_btn', 'close_btn5', 'start_game'], timeout=90)

            for _ in range(5):
                try:
                    name = await self.player.find_then_click(['close_btn', 'close_btn5', 'start_game'])
                    await asyncio.sleep(2)
                    if name == 'start_game':
                        await self.player.find_then_click(['close_btn', 'close_btn5', 'start_game'])
                        break
                except FindTimeout:
                    self.logger.warning("start game failed")
                    return False

            # TODO: 账号异地登陆

            # pos_start_game = (430, 490)
            # await self.player.click(pos_start_game)
            # await asyncio.sleep(3)
            name, pos = await self.player.monitor(['setting', 'game_91'])
            if name == 'game_91':
                pos_login = (430, 350)
                await self.player.click(pos_login, delay=3)
                name, pos = await self.player.monitor(['setting', 'game_91'])
                if name == 'game_91':
                    self.logger.debug("_login_game failed.")
                    return False
                else:
                    await self._close_ad(timeout=5)
                    return True
            else:
                await self._close_ad(timeout=5)
                return True

        if not account_pre:
            sucess = await _login_game()
            if not sucess:
                await self._close_game()
                sucess = await _login_game()
                if not sucess:
                    return False

            # 现在，只有3个用户，不需要切换账号、服务器
            # await _login_account()
            # await _login_server()
        else:
            if account_curr.game_name != account_pre.game_name:
                await self._close_game()
                sucess = await _login_game()
                if not sucess:
                    await self._close_game()
                    sucess = await _login_game()
                    if not sucess:
                        return False
                # await _login_account()
                # await _login_server()
            # elif account_curr.account != account_pre.account:
            #     await _login_account()
            #     await _login_server()
            # else:
            #     await _login_server()

        return True

    async def play_game(self):
        tasks = [
            'maze',
            'collect_mail',
            'vip_shop',
            'friends_interaction',
            'community_assistant',
            'instance_challenge',
            'guild',
            'exciting_activities',
            'jedi_space',
            'survival_home',
            'market',
            'invite_heroes',
            'level_battle',
            'arena',
            'arena_champion',
            'task_board',
            'armory',
            'lucky_draw',
            'tower_battle',
            'brave_instance',
            'hero_expedition',
        ]

        count = 0
        for task in tasks:
            if not need_run(task):
                self.logger.debug("skip to run {task}")
                continue

            self.logger.info("Start to run: " + task)
            try:
                await self.goto_main_interface()
                await getattr(self, task)()
            except FindTimeout as e:
                count += 1
                self.logger.warning(str(e))
                self.save_operation_pics(str(e))
            except Exception as e:
                count += 1
                self.logger.error(str(e))
                self.save_operation_pics(str(e))

            if count > 5:
                self.logger.error('Timeout too many times, so exit')
                break

        # 回到主界面，避免切账号报错
        await self.goto_main_interface()


def need_run(name):
    def is_pm():
        t = time.localtime()
        hour = t.tm_hour
        return hour > 12

    def is_odd_day():
        t = time.localtime()
        day = t.tm_mday
        return day % 2 == 1

    def is_sunday():
        t = time.localtime()
        # day of week, range [0, 6], Monday is 0
        wday = t.tm_wday
        return wday == 6

    if name == 'arena_champion':
        # return True
        if is_sunday() and is_pm():
            return True
        else:
            logger.debug(f"Skip to run {name}, for it isn't sunday PM now.")
            return False

    if name in ['arena', 'armory', 'invite_heroes', 'jedi_space', 'brave_instance', 'lucky_draw', 'task_board', 'vip_shop', 'tower_battle', 'maze']:
        # 只在下午运行
        if is_pm():
            return True
        else:
            logger.debug(f"Skip to run {name}, for it isn't PM now.")
            return False
    else:
        return True


async def play(window_name, account_list, g_queue, g_event, g_found, g_player_lock):
    player = Player(window_name, g_queue, g_event,
                    g_found, g_player_lock)
    auto_play = AutoPlay(player)

    # await auto_play.play_game()

    try:
        # 如果游戏已经启动，直接开玩
        await player.monitor(['setting'], timeout=1)
        return await auto_play.play_game()
    except FindTimeout:
        pass

    try:
        await player.monitor(['emulator_started'], timeout=60)
    except FindTimeout:
        logger.warning("Start the emulator failed.")
        return

    await asyncio.sleep(5)

    pos_close_remind = (680, 200)
    try:
        await player.monitor(['remind'], timeout=1)
        await player.click(pos_close_remind)
    except FindTimeout:
        pass

    pos_close_app = (300, 300)
    while True:
        try:
            await player.monitor(['app_error'], timeout=1)
            await player.click(pos_close_app)
        except FindTimeout:
            break

    account_pre = None
    Account = namedtuple(
        'Account', ['game_name', 'account', 'passwd', 'server'])

    while account_list:
        account_dict = account_list.pop()
        logger.debug(
            f'{window_name}: account_list: {account_list} account_dict: {account_dict}')
        logger.debug("remain account_list:" + str(len(account_list)))
        game_name = account_dict['game_name']
        account = account_dict['account']
        passwd = account_dict['passwd']
        server_ids = account_dict['server_ids']

        if server_ids:
            for server in server_ids:
                account_curr = Account(game_name, account, passwd, server)
                success = await auto_play.login(account_pre, account_curr)
                if not success:
                    logger.warning(f"{window_name} login failed.")
                    return
                account_pre = account_curr
                await auto_play.play_game()
        else:
            account_curr = Account(game_name, account, passwd, '')
            success = await auto_play.login(account_pre, account_curr)
            if not success:
                logger.warning(f"{window_name} login failed.")
                return
            account_pre = account_curr
            await auto_play.play_game()


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

# TODO 把文字截图都替换掉，文字匹配偶尔会不准

# TODO 监控boos，设别率太低

# TODO 英雄列表已满

# TODO 页面不打debug，只打印info，每个任务，skip原因

# TODO 解决图像识别率达不够高，导致bug的问题

# TODO 自动删除n天前的好友

# add one line

# TODO timeout 改成10s， 每次切界面都要保证切换成功了

# TODO 在主界面移动 作为一个独立的任务来做，因为安排得当，是不需要太多移动的
