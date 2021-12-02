# -*-coding:utf-8-*-
##############################################################################
# 模拟人类玩家
# 
#
##############################################################################


from lib.ui_data import POS_DICT, WINDOW_DICT, WIDTH, HIGH
from lib import player_hand
from lib import eye
import asyncio
import random

import logging
logger = logging.getLogger(__name__)




def _get_first(lst):
    return lst[0]

class Player(object):
    def __init__(self, g_lock, window=None):
        self.g_lock = g_lock
        self.window = window
        self.eye = eye.Eye()
        self.hand = player_hand.Hand()


    async def monitor(self, names, timeout=10, threshold=0.8, filter_func=_get_first):
        """return (name, pos), all rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        name, pos_list = await self.eye.monitor(names, area=self.window.bbox, timeout=timeout, threshold=threshold)
        pos = filter_func(pos_list)
        logger.debug(f"found {name} at {pos}")

        return name, pos

    async def find_all_pos(self, names, threshold=0.8):
        """return (name, pos), all rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        pos_list = await self.eye.find_all_pos(names, area=self.window.bbox, threshold=threshold)

        return pos_list

    async def click(self, pos, delay=1, cheat=True):
        if cheat:
            x = pos[0] + random.randint(-10, 10)
            y = pos[1] + random.randint(-8, 8)
        else:
            x = pos[0] + random.randint(-2, 2)
            y = pos[1] + random.randint(-2, 2)
        pos = self.window.real_pos((x, y))

        logger.debug(f"click screen at {pos}")
        async with self.g_lock:
            await self.hand.click(pos)
        await asyncio.sleep(delay)

    async def double_click(self, pos, delay=1, cheat=True):
        if cheat:
            x = pos[0] + random.randint(-10, 10)
            y = pos[1] + random.randint(-8, 8)
        else:
            x = pos[0] + random.randint(-2, 2)
            y = pos[1] + random.randint(-2, 2)
        pos = self.window.real_pos((x, y))

        logger.debug(f"double-click screen at {pos}")
        async with self.g_lock:
            await self.hand.double_click(pos)
        await asyncio.sleep(delay)

    async def drag(self, p1, p2, speed=0.05, delay=0.2):
        """drag from position 1 to position 2"""
        p1, p2 = map(self.window.real_pos, [p1, p2])
        logger.debug(f"drag from {p1} to {p2}")
        async with self.g_lock:
            await self.hand.drag(p1, p2, speed)
        await asyncio.sleep(delay)

    async def scroll(self, vertical_num, delay=0.2):
        if vertical_num < 0:
            logger.debug(f"scroll down {vertical_num}")
        else:
            logger.debug(f"scroll up {vertical_num}")
        async with self.g_lock:
            await self.hand.scroll(vertical_num)
        await asyncio.sleep(delay)

    async def move(self, x, y, delay=0.2):
        x, y = self.real_pos((x, y))
        logger.debug(f"move to ({x}, {y})")
        async with self.g_lock:
            await self.hand.move(x, y)
        await asyncio.sleep(delay)

    async def tap_key(self, key, delay=1):
        """tap a key with a random interval"""
        logger.debug(f"tap_key {key}")
        async with self.g_lock:
            await self.hand.tap_key(key)
        await asyncio.sleep(delay)


