import time
import os
import asyncio
import shutil
import datetime
import re
import random
from operator import itemgetter
from playsound import playsound
from ui_data import SCREEN_DICT
from player import Player, FindTimeout

import logging
logger = logging.getLogger(__name__)

skip_fight = None


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


class AutoPlay(object):
    def __init__(self, player):
        self.player = player

    #
    # public functions
    #
    async def _move_to_left_top(self):
        logger.debug('_move_to_left_top')
        p1 = (200, 300)
        p2 = (800, 400)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def _move_to_right_top(self):
        logger.debug('_move_to_right_top')
        p1 = (700, 200)
        p2 = (200, 400)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def _move_to_center(self):
        logger.debug('_move_to_center')
        await self._move_to_left_top()
        p1 = (500, 300)
        p2 = (200, 300)
        await self.player.drag(p1, p2)

    async def _move_to_left_down(self):
        logger.debug('_move_to_left_down')
        p1 = (200, 400)
        p2 = (700, 200)
        await self.player.drag(p1, p2)
        await self.player.drag(p1, p2)

    async def goto_main_interface(self):
        for _ in range(5):
            try:
                _, pos = await self.player.monitor(['setting'], timeout=1)
                # await self.player.click((855, 45), cheat=False)    # 去掉一些遗留界面
                break
            except FindTimeout:
                await self.player.go_back()
        else:
            msg = "goto main interface failed"
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
        for _ in range(6):
            await self.player.click((x, y), delay=0.2)
            x += dx

        return True

    async def _fight(self):
        """do fight, return win or lose"""
        _, pos = await self.player.monitor(['start_fight', 'fight1'])
        await self.player.click(pos, delay=3)

        try:
            _, pos = await self.player.monitor(['fast_forward1'], timeout=1)
            await self.player.click(pos)
        except FindTimeout:
            pass

        await asyncio.sleep(10)

        name, pos = await self.player.monitor(['go_last', 'win', 'lose'], timeout=240)
        if name == 'go_last':
            await self.player.click(pos)
            name, pos = await self.player.monitor(['win', 'lose'], timeout=240)
        pos_ok = (430, 430)
        await self.player.click(pos_ok, delay=3)

        return name

    #
    # level_battle
    #

    async def _nextlevel_to_fight(self, pos):
        """go from next_level to fight"""
        await self.player.click(pos)
        try:
            name, pos = await self.player.monitor(['search', 'level_map'])
        except FindTimeout:
            return False
            # 打到当前等级的关卡上限了
        if name == 'search':
            await self.player.click(pos)
            await asyncio.sleep(10)    # TODO vip no need 10s
        else:
            # await asyncio.sleep(3)
            # _, pos = await self.player.monitor(['point'], threshold=0.9, filter_func=filter_rightmost)
            await asyncio.sleep(5)
            pos_list = await self.player.find_all_pos(['point', 'point3'], threshold=0.9)
            pos = filter_rightmost(pos_list)
            # 往右偏移一点，刚好能点击进入到下一个大关卡
            await self.player.click((pos[0] + 50, pos[1]))
            _, pos = await self.player.monitor(['ok1'])
            await self.player.click(pos)
            await asyncio.sleep(10)

        _, pos = await self.player.monitor(['fight'])
        await self.player.click(pos)
        return True

    async def _passed_to_fight(self):
        """go from already_passed to fight"""
        try:
            name, pos = await self.player.monitor(['next_level2', 'next_level3'], threshold=0.85)
        except FindTimeout:
            return False
        await self.player.click(pos, cheat=False)
        _, pos = await self.player.monitor(['search'])
        await self.player.click(pos)
        await asyncio.sleep(10)
        _, pos = await self.player.monitor(['fight'])
        await self.player.click(pos)
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
            await self.goto_main_interface()
            await self._move_to_center()
            _, pos = await self.player.monitor(['level_battle'])
            await self.player.click(pos, delay=3)
        finally:
            name, pos = await self.player.monitor(['next_level1', 'already_passed', 'fight'])

        return (name, pos)

    async def level_battle(self):
        """关卡战斗"""
        await self._move_to_center()
        name, pos = await self.player.monitor(['level_battle'])
        await self.player.click(pos, delay=3)

        pos_box = (750, 470)
        await self.player.click(pos_box)
        try:
            _, pos = await self.player.monitor(['receive'])
            await self.player.click(pos, delay=2)
        except FindTimeout:
            pass

        name, pos = await self.player.monitor(['upgraded', 'next_level1', 'already_passed', 'fight'])
        if name == 'upgraded':
            name, pos = await self._hand_upgraded()

        if name == 'next_level1':
            success = await self._nextlevel_to_fight(pos)
            if not success:
                return await self.goto_main_interface()
        elif name == 'already_passed':
            success = await self._passed_to_fight()
            if not success:
                return await self.goto_main_interface()
        else:
            await self.player.click(pos)

        while True:
            res = await self._fight()

            if res == 'lose':
                logger.debug('Fight fail, so exit')
                # 打不过，就需要升级英雄，更新装备了
                return await self.goto_main_interface()

            try:
                name, pos = await self.player.monitor(['upgraded', 'next_level1'])
            except FindTimeout:
                # 打到最新关了
                return await self.goto_main_interface()

            if name == 'upgraded':
                name, pos = await self._hand_upgraded()

            await self._nextlevel_to_fight(pos)

    #
    # tower_battle
    #

    async def tower_battle(self):
        await asyncio.sleep(1)
        await self._move_to_right_top()

        _, pos = await self.player.monitor(['warriors_tower'])
        await self.player.click(pos, delay=2)
        pos_list = [
            (150, 360),
            (400, 360),
            (650, 360),
        ]

        while True:
            for pos in pos_list:
                await self.player.click(pos, delay=0.2)
            await asyncio.sleep(1)

            _, pos = await self.player.monitor(['challenge'])
            await self.player.click(pos)

            res = await self._fight()

            if res == 'lose':
                logger.debug('Fight fail, so exit')
                # 打不过，就需要升级英雄，更新装备了
                return await self.goto_main_interface()

    #
    # collect_mail
    #

    async def collect_mail(self):
        try:
            _, pos = await self.player.monitor(['mail'], threshold=0.97, timeout=1)
        except FindTimeout:
            logger.debug("There is no new mail.")
            return
        await self.player.click(pos)
        _, pos = await self.player.monitor(['one_click_collection'])
        await self.player.click(pos)
        await self.goto_main_interface()

    #
    # friends_interaction
    #

    async def _fight_friend(self, max_try=3):
        max_try = max_try
        count = 0
        pos_ok_win = (430, 430)
        pos_ok_lose = (340, 430)
        pos_next = (530, 430)
        _, pos_fight = await self.player.monitor(['start_fight'])
        global skip_fight
        if skip_fight is None:
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
        except FindTimeout:
            logger.debug("There is no new interaction of friends.")
            return

        await self.player.click(pos)
        _, pos = await self.player.monitor(['receive_and_send'])
        await self.player.click(pos)

        try:
            _, pos = await self.player.monitor(['friends_help'], threshold=0.9, timeout=1)
        except FindTimeout:
            logger.debug("There is no friend need help.")
            await self.goto_main_interface()
            return

        await self.player.click(pos)

        while True:
            try:
                _, (x, y) = await self.player.monitor(['search1'], threshold=0.9, timeout=1)
                pos = (x, y + 15)
                await self.player.click(pos)
            except FindTimeout:
                logger.debug("There is no more boss.")
                await self.goto_main_interface()
                return

            name, pos = await self.player.monitor(['fight2', 'ok', 'ok9'])
            if name in ['ok', 'ok9']:
                await self.goto_main_interface()
                return

            await self.player.click(pos)
            _, pos = await self.player.monitor(['fight3'])
            await self.player.click(pos)

            res = await self._fight_friend()
            if res != 'win':
                logger.debug("Can't win the boos")
                await self.goto_main_interface()
                return

    #
    # community_assistant
    #

    async def community_assistant(self):
        _, pos = await self.player.monitor(['community_assistant'])
        await self.player.click(pos)

        try:
            _, pos = await self.player.monitor(['guess_ring'], threshold=0.97, timeout=1)
            await self.player.click(pos, delay=2)
        except FindTimeout:
            logger.debug("Fress guess had been used up.")
            await self.goto_main_interface()
            return

        _, pos = await self.player.monitor(['cup'])
        await self.player.click(pos, delay=4)
        for _ in range(2):
            _, pos = await self.player.monitor(['next_game'])
            await self.player.click(pos, delay=2)
            try:
                _, pos = await self.player.monitor(['cup'])
                await self.player.click(pos, delay=4)
            except FindTimeout:
                break

        await self.player.go_back()
        try:
            _, pos = await self.player.monitor(['have_a_drink'], timeout=2)
            await self.player.click(pos, delay=5)
        except FindTimeout:
            pass

        _, pos = await self.player.monitor(['gift'])
        await self.player.click(pos)
        pos_select_gift = (70, 450)
        pos_send_gift = (810, 450)
        while True:
            try:
                _, pos = await self.player.monitor(['gift_over'], threshold=0.92, timeout=1)
                break
            except FindTimeout:
                await self.player.click(pos_select_gift, delay=0.2)
                await self.player.click(pos_send_gift)
                try:
                    _, pos = await self.player.monitor(['start_turntable'], timeout=1)
                    await self.player.click(pos)
                    await asyncio.sleep(5)
                except FindTimeout:
                    pass

        await self.goto_main_interface()

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
            logger.debug("No new challenge.")
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
            await self.player.click(pos)
            if name == 'start_fight':
                await asyncio.sleep(3)
                res = await self._fight_challenge()
                if res != 'win':
                    logger.debug("Fight lose")
                else:
                    await self.player.click(pos_next, delay=3)
                    await self._fight_challenge()
                await self.player.click(pos_ok, delay=3)
            else:
                await self.player.click(pos_next)
                await self.player.click(pos_ok)

            await self.player.go_back()

        await self.goto_main_interface()

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
            logger.debug("No new guild event.")
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
        pos_list = await self.player.find_all_pos(['start_order'])
        for pos in pos_list:
            await self.player.click(pos)
        await self._move_to_right_top()
        pos_list = await self.player.find_all_pos(['start_order'])
        for pos in pos_list:
            await self.player.click(pos)

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
        pos_boxes = [
            (200, 170),
            (310, 170),
            (540, 170),
            (700, 170),
        ]
        pos_list = await self.player.find_all_pos(['box1'], threshold=0.9)
        for p in sorted(pos_list):
            await self.player.click(p)
            _, pos = await self.player.monitor(['ok4', 'ok13'], timeout=2)
            await self.player.click(pos)

        await self.goto_main_interface()

    #
    # exciting_activities
    #
    async def exciting_activities(self):
        pos_exciting_activities = (740, 70)
        await self.player.click(pos_exciting_activities)
        pos_sign_in = (700, 430)
        await self.player.click(pos_sign_in)
        await self.goto_main_interface()

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

        # done 这里要改成图像识别，因为点击pos_mop_up的结果不是确定的
        try:
            _, pos_plus = await self.player.monitor(['plus'], threshold=0.98, timeout=1)
        except FindTimeout:
            return await self.goto_main_interface()
        for _ in range(5):
            await self.player.click(pos_plus, cheat=False, delay=0.2)
        pos_ok1 = (420, 360)
        await self.player.click(pos_ok1)

        await self.goto_main_interface()

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

        global skip_fight
        if skip_fight is None:
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
        for pos in pos_list:
            await self.player.click(pos, delay=0.2)

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
        skip_last_map = False
        map_count = 0
        pos_switch_map = (50, 470)
        for num in [-5, 5]:
            await self.player.move(50, 350)
            await self.player.scroll(num)
            await asyncio.sleep(1)
            await self.player.move(150, 350)
            map_list = await self.player.find_all_pos(['field_map'])
            map_list = sorted(map_list, key=lambda x: x[1], reverse=True)

            # 一般，最下那层是打不过的
            if not skip_last_map:
                if len(map_list) > 0:
                    new_map_list = map_list[1:]
                    skip_last_map = True
                else:
                    new_map_list = map_list
            else:
                new_map_list = map_list

            for pos in new_map_list:
                await self.player.click(pos, delay=2)
                pos_list = await self.player.find_all_pos(['boss'], threshold=0.65)
                if pos_list:
                    map_count += 1
                    # 太低层的怪也没必要打
                    if map_count > 2:
                        logger.debug(f"map_count: {map_count}, so return")
                        return await self.goto_main_interface()
                    for p1 in pos_list:
                        await self.player.click(p1, cheat=False)
                        _, p2 = await self.player.monitor(['fight6'])
                        await self.player.click(p2)
                        res = await self._fight_home()
                        if res != 'win':
                            # 打不过，就去打上一层
                            break
                    # 战斗后，地图可能会缩回去
                    try:
                        await self.player.monitor(['field_map'], timeout=1)
                    except FindTimeout:
                        await self.player.click(pos_switch_map)

        await self.goto_main_interface()

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

        await self.goto_main_interface()

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
                await self.goto_main_interface()
                await self._dismiss_heroes()
                _, pos = await self.player.monitor(['invite_hero'])
                await self.player.click(pos, delay=2)

        await self.goto_main_interface()

    #
    # armory
    #

    async def armory(self):
        # "armory": "./pics/armory/armory.jpg",
        # "arms": "./pics/armory/arms.jpg",
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
        for i in range(len_num):
            pos_type = pos_types[(idx + i) % len_num]
            await self.player.click(pos_type)
            # 匹配上所有点，但排除右边pos_types的那些点
            pos_list = await self.player.find_all_pos(['arms'], threshold=0.8)
            pos_list = list(filter(lambda x: x[0] < 800, pos_list))
            if pos_list:
                pos_list = sorted(pos_list, key=itemgetter(1, 0))
                pos = pos_list[0]
                pos = (pos[0] - 30, pos[1] + 30)
                await self.player.click(pos)
                await self.player.click(pos_quantity)
                await self.player.tap_key('3')
                await self.player.click(pos_enter)
                await self.player.click(pos_forging)
                break
        else:
            logger.info("There are not enough equipment for synthesis.")

        await self.goto_main_interface()
        return

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

        # pics3 = ['hero_badge', 'task_ticket']
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
                        logger.debug('lack of gold')
                        return await self.goto_main_interface()
            try:
                name, pos = await self.player.monitor(['refresh2'], threshold=0.9, timeout=1)
                # name, pos = await self.player.monitor(['refresh', 'refresh1', 'refresh2', 'refresh3'], threshold=0.92, timeout=2)
                await self.player.click(pos)
                # if name == 'refresh3':
                #     _, pos = await self.player.monitor(['ok8'])
                #     await self.player.click(pos)
            except FindTimeout:
                return await self.goto_main_interface()

        await self.goto_main_interface()

    #
    # arena
    #

    async def _fight_arena(self):
        _, pos_fight = await self.player.monitor(['start_fight'])

        global skip_fight
        if skip_fight is None:
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
                logger.debug('Fight lose.')
                break

        try:
            _, pos = await self.player.monitor(['reward'], timeout=1, threshold=0.9)
            await self.player.click(pos)
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

        await self.goto_main_interface()

    #
    # brave_instance
    #

    async def _fight_brave(self):
        _, pos_fight = await self.player.monitor(['start_fight'])

        global skip_fight
        if skip_fight is None:
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
            res = 'win'
        else:
            res = 'lose'

        pos_ok = (430, 430)
        await self.player.click(pos_ok)
        if not skip_fight:
            await asyncio.sleep(3)

        return res

    async def brave_instance(self):
        """勇者副本"""
        await self._move_to_right_top()
        _, pos = await self.player.monitor(['brave_instance'])
        await self.player.click(pos)
        await self._move_to_left_down()

        for i in range(15):
            _, (x, y) = await self.player.monitor(['current_level'], threshold=0.96)
            pos = (x, y + 40)
            await self.player.click(pos, cheat=False)
            _, pos = await self.player.monitor(['challenge4'])
            await self.player.click(pos)
            if i == 0:
                await self._equip_team()
            res = await self.fight_brave()
            if res == 'lose':
                break

        await self.goto_main_interface()


def save_timeout_pic(msg):
    screen_pic = SCREEN_DICT['screen']
    timestr = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    monitor_items = re.search(r'\[.+\]', msg).group()
    log_pic = os.path.join('./timeout_pics', f"{timestr}_{monitor_items}.jpg")
    shutil.copyfile(screen_pic, log_pic)
    logger.info(f"save_timeout_pic: {monitor_items}")
    playsound('./sounds/error.mp3')


def need_run(name):
    def is_pm():
        t = time.localtime()
        hour = t.tm_hour
        return hour > 12

    def is_odd_day():
        t = time.localtime()
        day = t.tm_mday
        return day % 2 == 1

    if name in ['arena', 'armory', 'invite_heroes', 'jedi_space']:
        # 只在下午运行
        if is_pm():
            return True
        else:
            logger.info(f"Skip to run {name}, for it isn't PM now.")
    elif name in ['brave_instance']:
        # 只在单数日期运行
        if is_odd_day() and is_pm():
            return True
        else:
            logger.info(
                f"Skip to run {name}, for it isn't odd day and PM now.")
    else:
        return True


async def play(windows_name, g_queue, g_event, g_found, g_hand_lock, g_player_lock):
    player = Player(windows_name, g_queue, g_event,
                    g_found, g_hand_lock, g_player_lock)
    auto_play = AutoPlay(player)
    tasks = [
        'collect_mail',
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
        'armory',
        'tower_battle',
        'brave_instance',
    ]
    count = 0
    for task in tasks:
        if not need_run(task):
            continue

        logger.info("Start to run: " + task)
        try:
            await getattr(auto_play, task)()
        except FindTimeout as e:
            count += 1
            save_timeout_pic(str(e))
            await auto_play.goto_main_interface()
            if count > 5:
                logger.error('Timeout too many times, so exit')
                break


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
