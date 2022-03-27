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


class PlayException(Exception):
    pass


class Task(object):
    def __init__(self, player):
        self.player = player
        self.logger = self.player.logger
        self._back_btn = (30, 60)

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
        p1 = (200, 200)
        p2 = (700, 400)
        await self.player.drag(p1, p2, speed=0.02)

    async def _move_to_right_top(self):
        self.logger.debug('_move_to_right_top')
        p1 = (600, 200)
        p2 = (200, 400)
        await self.player.drag(p1, p2, speed=0.02)

    async def _move_to_center(self):
        self.logger.debug('_move_to_center')
        await self._move_to_left_top()
        p1 = (500, 300)
        p2 = (200, 300)
        await self.player.drag(p1, p2)

    async def _move_to_left_down(self):
        self.logger.debug('_move_to_left_down')
        p1 = (200, 400)
        p2 = (600, 200)
        await self.player.drag(p1, p2, speed=0.02)


class LevelBattle(Task):
    def __init__(self, player):
        super().__init__(player)
        self.cfg = self.player.role_cfg

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
