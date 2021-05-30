# -*-coding:utf-8-*-
##############################################################################
# 模拟人手，进行鼠标、键盘输入
# 鼠标：click, drag, scroll, move
# 键盘：tap_key， tap_string
#
##############################################################################

import random
from pymouse import PyMouse
from pykeyboard import PyKeyboard
import asyncio
import math
from time import sleep
# from global_val import self.g_hand_lock
# from main import self.g_hand_lock

import logging
logger = logging.getLogger(__name__)


def distance(p1, p2):
    x = (p1[0] - p2[0]) ** 2
    y = (p1[1] - p2[1]) ** 2
    dist = math.sqrt(x + y)
    return dist


class Hand(object):
    m = PyMouse()
    k = PyKeyboard()
    err = 0.05
    interval = 0.04
    KEY_DICT = {
        'esc': k.escape_key
    }

    def __init__(self, g_hand_lock):
        self.g_hand_lock = g_hand_lock

    async def delay(self, n):
        """delay n seconds, with a random +- err error."""
        random_err = (-n + 2*n*random.random()) * self.err
        await asyncio.sleep(n + random_err)

    async def click(self, pos, cheat=True):
        """simulate a player to do a left-click"""
        if cheat:
            x = pos[0] + random.randint(-8, 8)
            y = pos[1] + random.randint(-5, 5)
        else:
            x, y = pos

        # async with self.g_hand_lock:
        self.m.click(x, y)
        await asyncio.sleep(0.2)
        logger.debug(f"click {pos}")


    async def drag(self, p1, p2, delay=0.2):
        """drag from position 1 to position 2"""
        x = p1[0]
        y = p1[1]
        step = 10

        # async with self.g_hand_lock:
        self.m.press(x, y)
        while distance((x, y), p2) >= 1:
            x += (p2[0] - x)/step
            y += (p2[1] - y)/step
            step -= 1
            self.m.move(int(x), int(y))
            await asyncio.sleep(0.02)
        self.m.release(p2[0], p2[1])

        await asyncio.sleep(delay)
        logger.debug(f"drag from {p1} to {p2}")

    async def scroll(self, vertical_num, delay=0.2):
        """垂直滚动"""
        num = vertical_num
        if num > 0:
            # async with self.g_hand_lock:
            while num > 0:
                num -= 1
                self.m.scroll(1)
                await asyncio.sleep(0.1)
        elif num < 0:
            # async with self.g_hand_lock:
            while num < 0:
                num += 1
                self.m.scroll(-1)
                await asyncio.sleep(0.1)
        else:
            if delay:
                await self.delay(delay)
            if vertical_num < 0:
                logger.debug(f"scroll down {vertical_num}")
            else:
                logger.debug(f"scroll up {vertical_num}")

    async def move(self, x, y, delay=0.2):
        # async with self.g_hand_lock:
        self.m.move(x, y)
        if delay:
            await self.delay(delay)

    async def tap_key(self, key, delay=0.2):
        """tap a key with a random interval"""
        if len(key) != 1:
            key = self.KEY_DICT[key]

        # async with self.g_hand_lock:
        self.k.press_key(key)
        await self.delay(self.interval)
        self.k.release_key(key)
        await self.delay(self.interval * 0.5)
        logger.debug(f"tap_key: {key}")
        if delay:
            await self.delay(delay)

    async def type_string(self, a_string, delay=0.2):
        """type a string to the computer"""
        # async with self.g_hand_lock:
        self.k.type_string(a_string)

        logger.debug(f"type_string {a_string}")
        if delay:
            await self.delay(delay)

    async def mouse_pos(self):
        return self.m.position()
