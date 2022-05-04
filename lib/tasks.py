from pickle import NEXT_BUFFER
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


class PlayException(Exception):
    pass


class Task(object):
    def __init__(self, player):
        self.player = player
        self.logger = self.player.logger
        self._back_btn = (30, 60)
        self.cfg = self.player.role_cfg

    def test(self):
        raise NotImplementedError()

    def run(self):
        raise NotImplementedError()

    async def _fight(self):
        """do fight, return win or lose"""
        await self.player.find_then_click(['start_fight', 'fight1'])
        await asyncio.sleep(3)
        res = await self._do_fight()
        pos_ok = (430, 430)
        await self.player.click(pos_ok)
        return res

    async def _do_fight(self):
        name_list = ['fast_forward1', 'go_last', 'win', 'lose']
        while True:
            name = await self.player.find_then_click(name_list, threshold=0.9, timeout=240)
            if name in ['win', 'lose']:
                return name
            else:
                name_list = name_list[name_list.index(name) + 1:]

    async def _move_to_left_top(self):
        self.logger.debug('_move_to_left_top')
        p1 = (150, 200)
        p2 = (650, 400)
        for i in range(3):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('dismiss_hero', timeout=1)
                return
            except FindTimeout:
                pass

    async def _move_to_right_top(self):
        self.logger.debug('_move_to_right_top')
        p1 = (600, 200)
        p2 = (100, 400)
        for i in range(3):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('warriors_tower', timeout=1)
                return
            except FindTimeout:
                pass

    async def _move_to_center(self):
        self.logger.debug('_move_to_center')
        await self._move_to_left_top()
        p1 = (450, 300)
        p2 = (200, 300)
        await self.player.drag(p1, p2)

    async def _move_to_left_down(self):
        self.logger.debug('_move_to_left_down')
        p1 = (100, 400)
        p2 = (600, 100)

        for i in range(3):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('market', timeout=1)
                return
            except FindTimeout:
                pass

    async def _move_to_right_down(self):
        self.logger.debug('_move_to_right_down')
        p1 = (700, 400)
        p2 = (100, 150)
        for i in range(3):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('bottom_right', timeout=1)
                return
            except FindTimeout:
                pass


class XianShiJie(Task):
    """现世界"""

    def __init__(self, player):
        super().__init__(player)

    async def test(self):
        return self.cfg['level_battle']['enable']

    async def run(self):
        await self._enter()
        await self._collect_box()

        while True:
            try:
                await self._goto_next_fight()
            except PlayException:
                await self.player.click(self._back_btn)
                return

            res = await self._fight()
            if res == 'lose':
                await self.player.monitor('ranking_icon')
                await self.player.click(self._back_btn)
                return

    async def _enter(self):
        try:
            await self.player.find_then_click('level_battle', timeout=1)
        except FindTimeout:
            await self._move_to_center()
            await self.player.find_then_click('level_battle')
        await self.player.monitor('ranking_icon')

    async def _collect_box(self):
        pos_box = (750, 470)
        await self.player.click(pos_box)
        await self.player.find_then_click('receive', raise_exception=False)

    async def _goto_next_fight(self):
        name, pos = await self.player.monitor(['upgraded', 'next_level', 'already_passed', 'fight'])
        if name == 'upgraded':
            await self._hand_upgraded()
            await self._goto_next_fight()
        elif name == 'next_level':
            await self._nextlevel_to_fight(pos)
        elif name == 'already_passed':
            await self._passed_to_fight()
        else:    # fight
            await self.player.click(pos)

    async def _hand_upgraded(self):
        try:
            await self.player.find_then_click('map_unlocked')
        except FindTimeout:
            return

        await asyncio.sleep(5)
        await self._enter()

    async def _nextlevel_to_fight(self, pos):
        """go from next_level to fight"""
        await self.player.click(pos)
        name, pos = await self.player.monitor(['search', 'level_map', 'level_low', 'reach_max_level'])
        if name == 'level_low' or name == 'reach_max_level':
            await self.player.click(pos)
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)
        elif name == 'search':
            await self.player.click(pos)
        else:
            await asyncio.sleep(5)
            pos_list = await self.player.find_all_pos(['point', 'point3'], threshold=0.9)
            pos = filter_rightmost(pos_list)
            # 往右偏移一点，刚好能点击进入到下一个大关卡
            await self.player.click((pos[0] + 50, pos[1]))
            await self.player.find_then_click('ok1')

        await asyncio.sleep(3)
        await self.player.find_then_click(['fight'])

    async def _passed_to_fight(self):
        """go from already_passed to fight"""
        await self.player.find_then_click(['next_level2', 'next_level3'], threshold=0.85)
        name, pos = await self.player.monitor(['search', 'level_low', 'reach_max_level'])
        if name == 'level_low' or name == 'reach_max_level':
            await self.player.click(pos)
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)
        await self.player.click(pos)
        await asyncio.sleep(3)
        await self.player.find_then_click(['fight'])


class Youjian(Task):
    """邮件"""

    def __init__(self, player):
        super().__init__(player)

    def test(self):
        return self.cfg['YouJian']['enable']

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('mail')
        try:
            # 邮件全部删除了，就没有领取按钮
            await self.player.find_then_click(['yi_jian_ling_qv'])
            # 已经领取过了，就不会弹出ok按钮
            await self.player.find_then_click(OK_BUTTONS)
        except FindTimeout:
            pass


class HaoYou(Task):
    """好友"""

    def __init__(self, player):
        super().__init__(player)

    async def run(self):
        if not self._test():
            return

        await self.player.find_then_click('friends')
        await self.player.find_then_click('receive_and_send')

        # 刷好友的boos
        for pos in await self.player.find_all_pos('friend_boss'):
            await self.player.click(pos)
            if not await self._fight_friend_boss():
                break

        # 刷自己的boos
        await self.player.find_then_click('friends_help')
        while True:
            if not await self._found_boos():
                break
            if not await self._fight_friend_boss():
                break

    def _test(self):
        return self.cfg['HaoYou']['enable']

    async def _fight_friend_boss(self):
        await self.player.find_then_click('fight3')
        try:
            await self.player.find_then_click('start_fight', timeout=3)
        except FindTimeout:
            self.logger.debug(f"Skip, lack of physical strength.")
            return False

        max_try = 5
        count = 0
        monitor_list = ['card', 'go_last', 'fast_forward1']

        while True:
            count += 1
            for _ in range(3):
                name, pos = await self.player.monitor(monitor_list, timeout=120)
                if name == "card":
                    await self.player.click(pos)
                    await asyncio.sleep(2)
                    await self.player.click(pos)
                    break
                else:
                    await self.player.click(pos)
                    monitor_list.remove(name)

            res, pos = await self.player.monitor(['win', 'lose'])
            if res == "win":
                await self.player.find_then_click(OK_BUTTONS)
                return True
            else:
                if count < max_try:
                    try:
                        await self.player.find_then_click('next2')
                    except:
                        self.logger.debug(f"Lose, lack of physical strength.")
                        return False
                else:
                    await self.player.find_then_click(OK_BUTTONS)
                    self.logger.debug(
                        f"Lose, reach the max fight try: {max_try}")
                    return False

    async def _found_boos(self):
        await self.player.monitor('hao_you_zhu_zhan')

        try:
            _, (x, y) = await self.player.monitor('search1', threshold=0.9, timeout=1)
            await self.player.click((x, y + 15))
        except FindTimeout:
            self.logger.debug("Can't search, search time not reached.")
            return False

        name = await self.player.find_then_click(['fight2', 'ok', 'ok9'])
        return name == "fight2"


class SheQvZhuLi(Task):
    """社区助理"""

    def __init__(self, player):
        super().__init__(player)

    async def run(self):
        if not self._test():
            return

        await self.player.find_then_click('community_assistant')

        if not await self._have_free_guess():
            return

        if not await self._found_right_assistant():
            return

        await self._play_guess_ring(max_num=4)
        await self.player.go_back_to('gift')
        await self._upgrade_Assistant()
        await self._send_gifts()

    def _test(self):
        return self.cfg['SheQvZhuLi']['enable']

    async def _have_free_guess(self):
        await self.player.monitor('gift')
        try:
            await self.player.monitor('ring', timeout=1)
        except FindTimeout:
            self.logger.debug("Skip, free guess had been used up.")
            return False
        return True

    async def _found_right_assistant(self):
        """从上往下，找到第一个未满级的助理"""
        pos_lsts = [(50, 240), (50, 330), (50, 400)]
        for pos in pos_lsts:
            try:
                # 达到60级，且满了，才看下一个
                await self.player.monitor('level_60', threshold=0.9, timeout=1)
                await self.player.monitor('level_full', threshold=0.9, timeout=1)
                await self.player.click(pos, delay=2)
            except FindTimeout:
                break

        try:
            await self.player.monitor('ring', timeout=1)
        except FindTimeout:
            self.logger.info("need buy the assistant first.")
            return False

        return True

    async def _play_guess_ring(self, max_num=4):
        for _ in range(max_num):
            await self.player.find_then_click(['ring', 'next_game'])
            await asyncio.sleep(2)
            name = await self.player.find_then_click(['cup', 'close', 'next_game'], timeout=1)
            if name != 'cup':
                break

    async def _upgrade_Assistant(self):
        try:
            await self.player.find_then_click('have_a_drink', timeout=1)
        except FindTimeout:
            pass

        await self.player.monitor('gift')
        await self.player.click((800, 255))    # 一键领取所有爱心
        await asyncio.sleep(2)

        try:
            await self.player.monitor('level_full', threshold=0.9, timeout=1)
        except FindTimeout:
            return

        await self.player.click((820, 75))    # 升级
        await self.player.find_then_click(OK_BUTTONS)

    async def _send_gifts(self):
        await self.player.find_then_click('gift')

        pos_select_gift = (70, 450)
        pos_send_gift = (810, 450)

        # 转转盘
        while True:
            try:
                await self.player.find_then_click('turntable', timeout=1)
                await self.player.click(pos_send_gift)
                await self.player.find_then_click('start_turntable')
            except FindTimeout:
                break
            await asyncio.sleep(5)

        # 送其它礼物
        while True:
            await self.player.click(pos_select_gift, delay=0.2)
            await self.player.click(pos_send_gift)
            try:
                await self.player.find_then_click('close_btn1', timeout=1)
                break
            except FindTimeout:
                pass


class TiaoZhanFuben(Task):
    """挑战副本"""

    def __init__(self, player):
        super().__init__(player)

    async def run(self):
        if not self._test():
            return

        await self.player.find_then_click('tiao_zhan_fu_ben')
        await self.player.monitor(CLOSE_BUTTONS)

        for (x, y) in await self.player.find_all_pos('red_point'):
            await self.player.click((x-50, y+20))

            button_name = await self._click_bottom_button()
            if button_name == 'sao_dang':
                await self._sao_dang()
            else:
                await self._tiao_zhan()

            await self.player.find_then_click(CLOSE_BUTTONS)

        await self.player.find_then_click(CLOSE_BUTTONS)

    def _test(self):
        return self.cfg['TiaoZhanFuben']['enable']

    async def _click_bottom_button(self):
        await self.player.monitor('dao_ji_shi')

        sao_dang_list = await self.player.find_all_pos(['mop_up', 'mop_up1', 'mop_up2'])
        tiao_zhan_list = await self.player.find_all_pos('challenge3')
        pos = filter_bottom(tiao_zhan_list + sao_dang_list)

        await self.player.click(pos)

        if pos in sao_dang_list:
            return 'sao_dang'
        return 'tiao_zhan'

    async def _sao_dang(self):
        await self.player.find_then_click('next_game1')
        await self.player.find_then_click(OK_BUTTONS)

    async def _tiao_zhan(self):
        await self.player.find_then_click('start_fight')
        res = await self._fight_challenge()

        if res == 'win':
            await self.player.find_then_click('xia_yi_chang')
            await self._fight_challenge()
        else:
            self.logger.warning("Fight lose in TiaoZhanFuben")

        await self.player.find_then_click(OK_BUTTONS)

    async def _fight_challenge(self):
        await self.player.find_then_click('go_last')
        await self.player.monitor('fight_report', timeout=240)
        res, _ = await self.player.monitor(['win', 'lose'])
        return res


class GongHui(Task):
    """公会"""

    def __init__(self, player):
        super().__init__(player)

    async def run(self):
        if not self._test():
            return

        await self.player.find_then_click('gong_hui')
        await self._gong_hui_qian_dao()

        await self.player.find_then_click('gong_hui_ling_di')
        await self._gong_hui_fu_ben()

        await self.player.go_back_to('guild_factory')
        await self._gong_hui_gong_chang()

    def _test(self):
        return self.cfg['GongHui']['enable']

    async def _gong_hui_qian_dao(self):
        await self.player.monitor('gong_hui_ling_di')
        await self.player.find_then_click('sign_in', threshold=0.95, timeout=1, raise_exception=False)

    async def _gong_hui_fu_ben(self):
        await self.player.find_then_click('gong_hui_fu_ben')

        name, pos = await self.player.monitor(['boss_card_up', 'boss_card_down'], threshold=0.92, timeout=3)
        # 匹配的是卡片边缘，而需要点击的是中间位置
        if name == 'boss_card_up':
            pos = (pos[0], pos[1]+50)
        else:
            pos = (pos[0], pos[1]-50)
        await self.player.click(pos)

        await self.player.monitor('ranking_icon2')
        try:
            await self.player.find_then_click('fight4', threshold=0.84, timeout=1)
        except FindTimeout:
            return

        await self._fight_guild()

    async def _fight_guild(self):
        go_last = (835, 56)
        next_fight = (520, 425)

        await self.player.find_then_click('start_fight')
        await self.player.monitor('message')
        await asyncio.sleep(2)
        # go_last 按钮有时候会被boos挡住，所以没用find_then_click
        await self.player.click(go_last)
        await self.player.monitor('fight_report', timeout=240)

        await self.player.click(next_fight)
        await self.player.monitor('message')
        await asyncio.sleep(2)
        await self.player.click(go_last)
        await self.player.monitor('fight_report', timeout=240)

        await self.player.find_then_click('ok')
        await self.player.monitor('ranking_icon2')

    async def _gong_hui_gong_chang(self):
        await self.player.find_then_click('guild_factory')

        try:
            for _ in range(2):
                await self.player.find_then_click(['order_completed', 'ok1'], timeout=3)
        except FindTimeout:
            pass

        await self.player.find_then_click('get_order')
        try:
            await self.player.monitor('start_order', timeout=1)
        except FindTimeout:
            pass
        else:
            await self.player.find_then_click('yi_jian_kai_shi_ding_dan')

        await self.player.find_then_click('donate_home')
        await self.player.find_then_click('donate')
        try:
            await self.player.find_then_click(['ok5'], timeout=2)
        except FindTimeout:
            pass


class MeiRiQianDao(Task):
    """每日签到"""

    def __init__(self, player):
        super().__init__(player)

    async def run(self):
        if not self._test():
            return

        await self.player.find_then_click('jing_cai_huo_dong')
        for _ in range(3):
            await self.player.find_then_click('qian_dao')

    def _test(self):
        return self.cfg['MeiRiQianDao']['enable']


class JueDiKongJian(Task):
    """绝地空间"""

    def __init__(self, player):
        super().__init__(player)

    async def run(self):
        if not self._test():
            return

        await self._move_to_left_top()
        await self.player.find_then_click('jedi_space')

        await self.player.find_then_click('challenge5')
        await self.player.find_then_click('mop_up3')

        try:
            await self.player.find_then_click(['max'], timeout=3, cheat=False)
        except FindTimeout:
            return

        await self.player.find_then_click(OK_BUTTONS)

    def _test(self):
        return self.cfg['JueDiKongJian']['enable']


class ShengCunJiaYuan(Task):
    """生存家园"""

    def __init__(self, player):
        super().__init__(player)

    async def run(self):
        if not self._test():
            return

        await self._move_to_left_top()
        await self.player.find_then_click('survival_home')
        await self._collect_resouces()

        await self.player.find_then_click('fight_btn')
        await self._fight_home_boos()

        await self.player.monitor('switch_map')
        await self._collect_all_boxes()

    def _test(self):
        return self.cfg['ShengCunJiaYuan']['enable']

    async def _collect_resouces(self):
        await self.player.monitor('zhu_ji_di')
        await asyncio.sleep(3)    # 点太快，可能卡住
        try:
            await self.player.find_then_click('resources', timeout=1)
        except FindTimeout:
            pass

    async def _fight_home_boos(self):
        max_fight = 4
        win_count = 0
        total_floors = await self._get_total_floors()

        # 从高层往低层打，战力高的话，可能多得一些资源
        # 战力低得话，可能就要浪费一些粮食了
        for i in range(total_floors, 3, -1):
            await self._goto_floor(i)
            for d in [None, 'left_top', 'left_down', 'right_down', 'right_top']:
                if d:
                    await self._swip_to(d)
                if await self._find_boos():
                    win = await self._fight()
                    if not win:
                        self.logger.warning(f"Fight lose, in floor: {i}")
                        break
                    win_count += 1
                    if win_count >= max_fight:
                        self.logger.debug(
                            f"stop fight, reach the max figh count: {max_fight}")
                        return
                    if await self._reach_point_limit():
                        self.logger.debug(f"stop fight, _reach_point_limit")
                        return

    async def _collect_all_boxes(self):
        try:
            await self.player.find_then_click('collect_all_box', timeout=1)
        except FindTimeout:
            return

        try:
            await self.player.find_then_click('receive3', timeout=3)
        except FindTimeout:
            return    # 可能以及收集完了

    async def _get_total_floors(self):
        await self.player.find_then_click('switch_map')
        await asyncio.sleep(1)

        locked_field = 0
        await self._drag_floors('up')
        map_list = await self.player.find_all_pos('locked_field')
        locked_field += len(map_list)
        if locked_field == 0:
            await self.player.find_then_click('switch_map')
            return 7

        await self._drag_floors('down')
        map_list = await self.player.find_all_pos('locked_field')
        locked_field += len(map_list)

        if locked_field >= 5:
            # 第四层没有解锁的话，会被重复统计
            floors = 7 - locked_field + 1
        else:
            floors = 7 - locked_field

        await self._drag_floors('up')
        await self.player.find_then_click('switch_map')
        return floors

    async def _drag_floors(self, d):
        pos1 = (55, 300)
        pos2 = (55, 400)
        if d == 'up':
            await self.player.drag(pos2, pos1, speed=0.02)
        elif d == 'down':
            await self.player.drag(pos1, pos2, speed=0.02)
        await asyncio.sleep(1)

    async def _goto_floor(self, i):
        pos_map = {
            1: (50, 288),
            2: (50, 321),
            3: (50, 356),
            4: (50, 388),
            5: (50, 341),
            6: (50, 375),
            7: (50, 409)
        }

        await self.player.find_then_click('switch_map')
        await asyncio.sleep(1)

        if i <= 4:
            await self._drag_floors('down')
        else:
            await self._drag_floors('up')

        await self.player.click(pos_map[i])
        await self.player.find_then_click('switch_map')

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

    async def _find_boos(self):
        await self.player.monitor('switch_map')
        pos_list = await self.player.find_all_pos(['boss', 'boss1', 'boss2'])
        for pos in pos_list:
            p_center = (pos[0] + 40, pos[1] - 40)
            if self._can_click(p_center):
                await self.player.click(p_center)
                return True
        return False

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

    async def _fight(self, max_try=2):
        pos_go_last = (836, 57)

        await self.player.find_then_click('fight6')

        for _ in range(max_try):
            await self.player.find_then_click(['start_fight', 'xia_yi_chang1'])
            await self.player.monitor('message')
            await self.player.click(pos_go_last)
            await self.player.monitor('fight_report', timeout=240)
            fight_res, _ = await self.player.monitor(['win', 'lose'], threshold=0.9)

            if fight_res == 'win':
                await self.player.find_then_click(OK_BUTTONS)
                return True

        await self.player.find_then_click(OK_BUTTONS)
        return False

    async def _reach_point_limit(self):
        # 如果达到了90或者95分，就不能再打boos了
        try:
            await self.player.monitor(['num_90', 'num_95'], threshold=0.9, timeout=1)
            return True
        except FindTimeout:
            return False
