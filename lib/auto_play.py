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
from playsound import playsound

from lib.ui_data import SCREEN_DICT
from lib.player import Player, FindTimeout

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

    #
    # public functions
    #
    async def _move_to_left_top(self):
        logger.debug(f'{self.player.window_name}: _move_to_left_top')
        p1 = (200, 300)
        p2 = (800, 400)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def _move_to_right_top(self):
        logger.debug(f'{self.player.window_name}: _move_to_right_top')
        p1 = (700, 200)
        p2 = (200, 400)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def _move_to_center(self):
        logger.debug(f'{self.player.window_name}: _move_to_center')
        await self._move_to_left_top()
        p1 = (500, 300)
        p2 = (200, 300)
        await self.player.drag(p1, p2)

    async def _move_to_left_down(self):
        logger.debug(f'{self.player.window_name}: _move_to_left_down')
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

    async def goto_main_interface(self):
        for _ in range(5):
            try:
                await self.player.monitor(['setting'], timeout=1)
                break
            except FindTimeout:
                await self.player.go_back()
        else:
            msg = f"{self.player.window_name}: [goto main interface failed]"
            save_timeout_pic(msg)
            logger.error(msg, exc_info=True)
            raise Exception(msg)

    async def _equip_team(self):
        try:
            _, _ = await self.player.monitor(['team_empty'], timeout=2)
        except FindTimeout:
            return True

        x = 120
        y = 450
        dx = 65
        pos_list = [(x, y)]
        for _ in range(5):
            x += dx
            pos_list.append((x, y))

        await self.player.multi_click(pos_list)

        return True

    async def _do_fight(self):
        name_list = ['fast_forward1', 'go_last', 'win', 'lose']
        while True:
            name = await self.player.find_then_click(name_list, timeout=240)
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
            logger.debug("reach the max level, so return")
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
            logger.debug("reach the max level, so return")
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
                logger.debug(f'{self.player.window_name}: Fight fail, so exit')
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
        await asyncio.sleep(2)

        pos_list = [
            (200, 360),
            (420, 360),
            (650, 360),
        ]

        while True:
            await self.player.monitor(['go_back'])
            await self.player.multi_click(pos_list)
            await asyncio.sleep(1)
            await self.player.find_then_click(['challenge'])
            res = await self._fight()
            if res == 'lose':
                logger.debug(f'{self.player.window_name}: Fight fail, so exit')
                # 打不过，就需要升级英雄，更新装备了
                return
            # await asyncio.sleep(2)

    #
    # collect_mail
    #
    async def collect_mail(self):
        try:
            _, pos = await self.player.monitor(['mail'], threshold=0.97, timeout=1)
        except FindTimeout:
            logger.debug(f"{self.player.window_name}: There is no new mail.")
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
            fight_res, pos = await self.player.monitor(['win', 'lose'])
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
            logger.debug(
                f"{self.player.window_name}: There is no new interaction of friends.")
            return

        await self.player.find_then_click(['receive_and_send'])

        try:
            _, pos = await self.player.monitor(['friends_help'], threshold=0.9, timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            logger.debug(
                f"{self.player.window_name}: There is no friend need help.")
            return

        while True:
            try:
                _, (x, y) = await self.player.monitor(['search1'], threshold=0.9, timeout=1)
                pos = (x, y + 15)
                await self.player.click(pos)
            except FindTimeout:
                logger.debug(
                    f"{self.player.window_name}: There is no more boss.")
                return

            name, pos = await self.player.monitor(['fight2', 'ok', 'ok9'])
            if name in ['ok', 'ok9']:
                return

            await self.player.click(pos)
            _, pos = await self.player.monitor(['fight3'])
            await self.player.click(pos)

            res = await self._fight_friend()
            if res != 'win':
                logger.debug(f"{self.player.window_name}:  Can't win the boos")
                return

    #
    # community_assistant
    #
    async def community_assistant(self):
        await self.player.find_then_click(['community_assistant'])

        try:
            _, pos = await self.player.monitor(['guess_ring'], threshold=0.97, timeout=2)
        except FindTimeout:
            logger.debug(
                f"{self.player.window_name}: Fress guess had been used up.")
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
            logger.info(
                f"{self.player.window_name}: need buy the assistant first.")
            return

        while True:
            try:
                name = await self.player.find_then_click(['close', 'cup'])
                if name == "close":
                    break
                name = await self.player.find_then_click(['close', 'next_game'])
                if name == "close":
                    break
            except FindTimeout:
                break

        await self.player.go_back()
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

        fight_res, pos = await self.player.monitor(['win', 'lose'], timeout=240)
        return fight_res

    async def instance_challenge(self):
        try:
            _, pos = await self.player.monitor(['Instance_challenge'], threshold=0.97, timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            logger.debug(f"{self.player.window_name}: No new challenge.")
            return

        challenge_list = await self.player.find_all_pos(['challenge2'], threshold=0.93)
        pos_ok = (430, 430)
        pos_next = (530, 430)
        for pos in challenge_list:
            await self.player.click(pos)
            pos_list = await self.player.find_all_pos(['challenge3', 'mop_up'])
            pos = filter_bottom(pos_list)
            await self.player.click(pos)
            name, pos = await self.player.monitor(['start_fight', 'next_game1'])

            if name == 'start_fight':
                await self.player.click(pos)
                await asyncio.sleep(3)
                res = await self._fight_challenge()
                if res != 'win':
                    logger.debug(f"{self.player.window_name}: Fight lose")
                else:
                    await self.player.click(pos_next, delay=3)
                    await self._fight_challenge()
                await self.player.click(pos_ok, delay=3)
            else:
                await self.player.click(pos_next)
                await self.player.click(pos_ok)

            await self.player.go_back()

    #
    # guild
    #

    async def _fight_guild(self):
        _, pos = await self.player.monitor(['start_fight'])
        await self.player.click(pos, delay=3)

        for _ in range(3):
            pos_list = await self.player.find_all_pos(['fast_forward1', 'go_last'], threshold=0.9)
            if pos_list:
                for pos in pos_list:
                    await self.player.click(pos)
                break
            await asyncio.sleep(1)

        _, pos = await self.player.monitor(['ok'], timeout=240)

        await self.player.click(pos, delay=3)

    async def guild(self):
        try:
            _, pos = await self.player.monitor(['guild'], threshold=0.97, timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            logger.debug(f"{self.player.window_name}: No new guild event.")
            return

        try:
            _, pos = await self.player.monitor(['sign_in'], threshold=0.95, timeout=1)
            await self.player.click(pos)
        except:
            pass
        pos_guild_territory = (700, 460)
        await self.player.click(pos_guild_territory)

        # guild_instance
        _, pos = await self.player.monitor(['guild_instance'])
        await self.player.click(pos)
        try:
            _, pos = await self.player.monitor(['boss_card'], threshold=0.92, timeout=2)
            # 匹配的是卡片边缘，而需要点击的是中间位置
            pos = (pos[0], pos[1]+50)
            await self.player.click(pos)
            _, (x, y) = await self.player.monitor(['fight4', 'fight5'], threshold=0.84, timeout=1)
            pos = (x-50, y-50)
            await self.player.click(pos)
            await self._fight_guild()
        except FindTimeout:
            pass

        # guild_factory
        for _ in range(2):
            await self.player.go_back()
            try:
                _, pos = await self.player.monitor(['guild_factory'], timeout=1)
                await self.player.click(pos)
                break
            except FindTimeout:
                pass

        try:
            _, pos = await self.player.monitor(['order_completed'], timeout=1)
            await self.player.click(pos)
            _, pos = await self.player.monitor(['ok1'])
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
    # survival_home
    #

    async def _fight_home(self, max_try=3):
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
            fight_res, pos = await self.player.monitor(['win', 'lose'], timeout=240)
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

    async def survival_home(self):
        await self._move_to_left_top()
        _, pos = await self.player.monitor(['survival_home'])
        await self.player.click(pos, delay=3)

        # pos_list = await self.player.find_all_pos(['food', 'gold', 'oil'])
        pos_list = await self.player.find_all_pos(['resources'], threshold=0.75)
        # for pos in pos_list:
        #     await self.player.click(pos, delay=0.2)
        if pos_list:
            await self.player.click(pos_list[0])

        pos_fight = (830, 490)
        await self.player.click(pos_fight)

        # collect box
        _, pos = await self.player.monitor(['switch_map'])
        await self.player.click(pos)
        for num in [-5, 5]:
            await self.player.move(50, 350)
            await self.player.scroll(num)
            await asyncio.sleep(1)
            await self.player.move(150, 350)    # 防遮挡
            map_list = await self.player.find_all_pos(['field_map'])
            map_list = sorted(map_list, key=lambda x: x[1], reverse=True)
            for pos in map_list:
                await self.player.click(pos, delay=2)
                pos_list = await self.player.find_all_pos(['box'])
                for p1 in pos_list:
                    await self.player.click(p1, delay=0.2)

        # fight boss
        # skip_last_map = False
        # map_count = 0
        # pos_switch_map = (50, 470)
        # for num in [-5, 5]:
        #     await self.player.move(50, 350)
        #     await self.player.scroll(num)
        #     await asyncio.sleep(1)
        #     await self.player.move(150, 350)
        #     map_list = await self.player.find_all_pos(['field_map'])
        #     map_list = sorted(map_list, key=lambda x: x[1], reverse=True)

        #     # 一般，最下那层是打不过的
        #     if not skip_last_map:
        #         if len(map_list) > 0:
        #             new_map_list = map_list[1:]
        #             skip_last_map = True
        #         else:
        #             new_map_list = map_list
        #     else:
        #         new_map_list = map_list

        #     for pos in new_map_list:
        #         await self.player.click(pos, delay=2)
        #         pos_list = await self.player.find_all_pos(['boss'], threshold=0.7)
        #         if pos_list:
        #             map_count += 1
        #             # 太低层的怪也没必要打
        #             if map_count > 2:
        #                 logger.debug(f"map_count: {map_count}, so return")
        #                 return
        #             for p1 in pos_list:
        #                 await self.player.click(p1, cheat=False)
        #                 _, p2 = await self.player.monitor(['fight6'])
        #                 await self.player.click(p2)
        #                 res = await self._fight_home()
        #                 if res != 'win':
        #                     # 打不过，就去打上一层
        #                     break
        #             # 战斗后，地图可能会缩回去
        #             try:
        #                 await self.player.monitor(['field_map'], timeout=1)
        #             except FindTimeout:
        #                 await self.player.click(pos_switch_map)

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
        await self.player.click(pos, delay=2)
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
            logger.info(
                f"{self.player.window_name}: There are not enough equipment for synthesis.")


    #
    # market
    #

    async def market(self):
        await asyncio.sleep(1)
        await self._move_to_left_down()
        _, pos = await self.player.monitor(['market'])
        await self.player.click(pos, delay=2)

        pos_get_gold = (410, 50)
        await self.player.click(pos_get_gold, cheat=False)
        for _ in range(2):
            try:
                _, pos = await self.player.monitor(['get_for_free2'], threshold=0.85, timeout=1)
                await self.player.click(pos)
                name, pos = await self.player.monitor(['ok9'], timeout=2)
                await self.player.click(pos)
            except FindTimeout:
                break
        await self.player.go_back()

        pics1 = ['hero_badge', 'task_ticket',
                 'soda_water1', 'soda_water2', 'soda_water3']
        offset1 = 40
        pics2 = ['hero_shard_3_1', 'hero_shard_3_2', 'hero_shard_3_3',
                 'hero_shard_3_4', 'hero_shard_4_1', 'hero_shard_4_2', 'hero_shard_4_3']
        offset2 = 10
        for _ in range(4):
            for pics, offset in [(pics1, offset1), (pics2, offset2)]:
                pos_list = await self.player.find_all_pos(pics, threshold=0.92)
                for pos in pos_list:
                    pos = (pos[0], pos[1] + offset)
                    await self.player.click(pos)
                    try:
                        _, pos = await self.player.monitor(['ok8'], timeout=1)
                        await self.player.click(pos)
                        name, pos = await self.player.monitor(['ok9', 'lack_of_gold'])
                    except FindTimeout:
                        continue  # 有些东西被购买了，还是能匹配到
                    if name == 'ok9':
                        await self.player.click(pos)
                    else:
                        logger.debug(
                            f'{self.player.window_name}: lack of gold')
                        return
            try:
                name, pos = await self.player.monitor(['refresh2'], threshold=0.9, timeout=1)
                await self.player.click(pos)
            except FindTimeout:
                return

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
        fight_res, pos = await self.player.monitor(['win', 'lose'])
        pos_ok = (430, 430)
        await self.player.click(pos_ok)
        if not skip_fight:
            await asyncio.sleep(4)

        return fight_res

    async def _swip_up(self):
        logger.debug(f'{self.player.window_name}: swipe_up')
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
                logger.debug(f'{self.player.window_name}: Fight lose.')
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

    async def arena_champion(self):

        await self.player.find_then_click(['arena'])
        await self.player.find_then_click(['champion'])
        await self.player.find_then_click(['enter'])

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

        while score < 50:
            await self.player.monitor('fight7')
            await self.player.click(pos_fight)    # 如果没有跳过战斗，按钮有个从下往上的动画
            await self.player.monitor('refresh_green')
            for _ in range(page):
                await self.player.click(pos_refresh, delay=0.3)
            await self.player.click(pos_fights[idx])
            await self.player.find_then_click(['fight_green'])
            for _ in range(10):
                name = await self.player.find_then_click(['card', 'ok12', 'next', 'go_last'])
                if name == 'card':
                    await self.player.click(pos_ok)
                    name = await self.player.find_then_click(['win', 'lose'])
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

        logger.info(f"win: {win}, lose: {lose}, score: {score}")


    #
    # brave_instance
    #

    async def _fight_brave(self):
        _, pos_fight = await self.player.monitor(['start_fight'])

        try:
            await self.player.monitor(['skip_fight'], threshold=0.9, timeout=1)
            skip_fight = True
        except FindTimeout:
            skip_fight = False

        await self.player.click(pos_fight)

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

        name, pos = await self.player.monitor(['card', 'lose'], timeout=240)
        if name == 'card':
            await self.player.click(pos)
            await self.player.click(pos)
            await asyncio.sleep(1)
            res = 'win'
        else:
            res = 'lose'

        return res

    async def brave_instance(self):
        """勇者副本"""
        await self._move_to_right_top()
        await self.player.find_then_click(['brave_instance'])
        await self._move_to_left_down()
        _, (x, y) = await self.player.monitor(['current_level'], threshold=0.96)
        pos = (x, y + 40)
        await self.player.click(pos, cheat=False)

        # pos_next = (530, 430)
        for i in range(15):
            _, pos = await self.player.monitor(['challenge4'])
            await self.player.click(pos)
            if i == 0:
                await self._equip_team()
            res = await self._fight_brave()
            if res == 'win':
                name, pos = await self.player.monitor(['next_level4', 'ok'])
                await self.player.click(pos)
                if name != 'next_level4':
                    _, (x, y) = await self.player.monitor(['current_level'], threshold=0.96)
                    pos = (x, y + 40)
                    await self.player.click(pos, cheat=False)
            else:
                await self.player.find_then_click('ok')
                break

    async def lucky_draw(self):
        await self.player.find_then_click(['lucky_draw'])
        await self.player.find_then_click(['draw_once'])
        await asyncio.sleep(8)
        await self.player.find_then_click(['draw_again'])

    async def _swipe_left(self):
        logger.debug(f'{self.player.window_name}: _swipe_left')
        p1 = (550, 300)
        p2 = (250, 300)
        await self.player.drag(p1, p2)
        await asyncio.sleep(1)

    async def _swipe_right_big(self):
        logger.debug(f'{self.player.window_name}: _swipe_right')
        p1 = (100, 300)
        p2 = (700, 300)
        await self.player.drag(p1, p2, speed=0.02)
        await asyncio.sleep(1)

    async def _goto_far_left(self):
        logger.debug(f'{self.player.window_name}: _goto_far_left')
        while True:
            await self._swipe_right_big()
            try:
                await self.player.monitor(['receivable_task'], timeout=1)
                break
            except FindTimeout:
                pass
        await self._swipe_right_big()    # 确保真的到最左边

    async def _accept_tasks(self, name_list):
        """return success_num, failed_num"""
        # ['task_3star', 'task_4star', 'task_5star', 'task_6star', 'task_7star']
        success_num = 0
        # failed_num = 0
        pos_battle = (350, 455)
        pos_start = (520, 455)
        pos_close = (725, 90)

        logger.info(f"accept_tasks: {name_list}")

        while True:
            pos_list = await self.player.find_all_pos(name_list, threshold=0.9)
            if pos_list:
                for pos in sorted(pos_list):
                    pos = (pos[0], pos[1] + 160)
                    await self.player.click(pos)
                    await self.player.monitor(['close'])
                    await self.player.click(pos_battle, delay=0.2)
                    await self.player.click(pos_start)
                    try:
                        await self.player.find_then_click(['close'], pos=pos_close, timeout=1)
                    except FindTimeout:
                        success_num += 1
                    else:
                        # failed_num += 1
                        logger.warning("There is a unacceptable tasks, so return")
                        # await self._swipe_left()
                        raise PlayException()
            else:
                try:
                    await self.player.monitor(['receivable_task'], timeout=1)
                except FindTimeout:
                    break    # 没有可以领取任务了
                else:
                    try:
                        await self.player.monitor(['unlock_more'], timeout=1)
                        break    # 划到最右边了
                    except FindTimeout:
                        pass

            await self._swipe_left()

        return success_num

    async def _finish_tasks(self, name_list, max_num=20):
        # ['finished_3star', 'finished_4star']
        pos_ok = (430, 380)
        pos_yes = (500, 350)
        num = 0

        logger.info(f"finish_tasks: {name_list}")

        while num < max_num:
            try:
                _, pos = await self.player.monitor(name_list, threshold=0.9, timeout=1)
            except FindTimeout:
                try:
                    await self.player.monitor(['unlock_more'], timeout=1)
                    break    # 划到最右边了
                except FindTimeout:
                    await self._swipe_left()
            else:
                pos = (pos[0], pos[1] + 160)
                await self.player.click(pos)
                if 'finished_5star' in name_list:
                    await self.player.click(pos_yes)
                await self.player.click(pos_ok)
                num += 1
        return num

    async def _add_tasks(self, num):
        """add new tasks, if success, return True"""
        logger.info(f"add_tasks: {num}")
        pos_use = (300, 480)
        for _ in range(num):
            await self.player.click(pos_use, delay=0.2)
        try:
            await self.player.monitor(['receivable_task'], timeout=1)
            return True
        except FindTimeout:
            logger.debug("there is no white task, so return")
            # 没有白信封了
            raise PlayException()

    async def _refresh_tasks(self):
        """refresh tasks"""
        logger.info("refresh_tasks")
        pos_refresh = (580, 480)
        await self.player.click(pos_refresh, delay=2)

        try:
            pos_cancel = (370, 350)
            await self.player.find_then_click(['no_diamond'], pos=pos_cancel, timeout=1)
            logger.warning('no enough diamond, so return')
            raise PlayException()
        except FindTimeout:
            pass

        try:
            await self.player.monitor(['receivable_task'], timeout=1)
            return
        except FindTimeout:
            await self._add_tasks(3)

    async def _count_5star_task(self):
        # 可能会多数
        num = 0
        while True:
            pos_list = await self.player.find_all_pos(['finished_5star'], threshold=0.9)
            num += len(pos_list)
            try:
                await self.player.monitor(['unlock_more'], timeout=1)
                break    # 划到最右边了
            except FindTimeout:
                await self._swipe_left()
        logger.debug(f"found {num} 5star tasks")
        return num


    async def task_board(self):
        # 如果有任务完成不了，就不要继续刷新任务了

        await self.player.find_then_click(['task_board'])
        try:
            await self.player.monitor(['receivable_task'])
        except:
            logger.debug("There is no receivable task")
            return

        # finish 3, 4 star tasks 
        await self._finish_tasks(['finished_3star', 'finished_4star'])
        await self._goto_far_left()

        try:
            # and then accept 3+ star tasks
            await self._accept_tasks(
                ['task_3star', 'task_4star', 'task_5star', 'task_6star', 'task_7star'])

            # refresh tasks and accept 3+ tasks
            await self._refresh_tasks()
            await self._accept_tasks(
                ['task_3star', 'task_4star', 'task_5star', 'task_6star', 'task_7star'])

            # finish 5 star task and then accept 3+ star tasks
            num = await self._count_5star_task()
            for _ in range(math.ceil(num / 2)):
                await self._finish_tasks(['finished_5star'], max_num=1)
                await self._refresh_tasks()
                await self._accept_tasks(
                    ['task_3star', 'task_4star', 'task_5star', 'task_6star', 'task_7star'])

        except PlayException():
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
            logger.debug("There is no maze")
            return

        await self.player.monitor(['maze_text'])

        try:
            await self.player.find_then_click(['maze_daily_gift'], threshold=0.9, timeout=1)
        except FindTimeout:
            logger.debug("maze daily gift have been already recived.")
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
            logger.debug("hero_expedition need at least one 14 star hero.")
            while True:
                name, pos = await self.player.monitor(['go_back', 'setting'])
                if name == 'go_back':
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
                logger.warning(
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
            await self.player.double_click(pos)
            await asyncio.sleep(50)

            try:
                _, pos = await self.player.monitor(['close_btn'], timeout=60)
                await self.player.click(pos)
            except FindTimeout:
                logger.warning(f"{self.player.window_name}: start game failed")
                return False

            # TODO: 账号异地登陆

            pos_start_game = (430, 490)
            await self.player.click(pos_start_game)
            await asyncio.sleep(3)
            name, pos = await self.player.monitor(['setting', 'game_91'])
            if name == 'game_91':
                pos_login = (430, 350)
                await self.player.click(pos_login, delay=3)
                name, pos = await self.player.monitor(['setting', 'game_91'])
                if name == 'game_91':
                    logger.debug(
                        f"{self.player.window_name} _login_game failed.")
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
                logger.debug(f"{self.player.window_name}: skip to run {task}")
                continue

            logger.info(f"{self.player.window_name}: Start to run: " + task)
            try:
                await self.goto_main_interface()
                await getattr(self, task)()
            except FindTimeout as e:
                count += 1
                save_timeout_pic(str(e))
                if count > 5:
                    logger.error('Timeout too many times, so exit')
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
        logger.warning(f"{window_name}: Start the emulator failed.")
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
        logger.debug(f'{window_name}: account_list: {account_list} account_dict: {account_dict}')
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
