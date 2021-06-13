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
        'esc': k.escape_key,
        'backspace': k.backspace_key,
    }

    async def delay(self, n):
        """delay n seconds, with a random +- err error."""
        random_err = (-n + 2*n*random.random()) * self.err
        await asyncio.sleep(n + random_err)

    async def click(self, pos, cheat=True, delay=0.1):
        """simulate a player to do a left-click"""
        if cheat:
            x = pos[0] + random.randint(-12, 12)
            y = pos[1] + random.randint(-8, 8)
        else:
            x = pos[0] + random.randint(-3, 3)
            y = pos[1] + random.randint(-2, 2)

        self.m.preess(x, y)
        await asyncio.sleep(0.2)
        self.m.release(x, y)
        await asyncio.sleep(delay)

    async def double_click(self, pos, cheat=True):
        """simulate a player to do a double left-click"""
        if cheat:
            x = pos[0] + random.randint(-12, 12)
            y = pos[1] + random.randint(-8, 8)
        else:
            x = pos[0] + random.randint(-3, 3)
            y = pos[1] + random.randint(-2, 2)

        self.m.click(x, y)
        self.m.click(x, y)
        await asyncio.sleep(0.1)

    async def drag(self, p1, p2, delay=0.2):
        """drag from position 1 to position 2"""
        x1 = p1[0] + random.randint(-12, 12)
        y1 = p1[1] + random.randint(-8, 8)
        x2 = p2[0] + random.randint(-12, 12)
        y2 = p2[1] + random.randint(-8, 8)
        step = 10

        self.m.press(x1, y1)
        while distance((x1, y1), (x2, y2)) >= 1:
            x1 += (x2 - x1)/step
            y1 += (y2 - y1)/step
            step -= 1
            self.m.move(int(x1), int(y1))
            await asyncio.sleep(0.05)
        self.m.release(x2, y2)

        await asyncio.sleep(delay)

    async def scroll(self, vertical_num, delay=0.2):
        """垂直滚动"""
        num = vertical_num + random.randint(-1, 1)
        if num > 0:
            while num > 0:
                num -= 1
                self.m.scroll(1)
                await asyncio.sleep(0.1)
        elif num < 0:
            while num < 0:
                num += 1
                self.m.scroll(-1)
                await asyncio.sleep(0.1)
        else:
            if delay:
                await self.delay(delay)

    async def move(self, x, y, delay=0.2):
        self.m.move(x, y)
        if delay:
            await self.delay(delay)

    async def tap_key(self, key, delay=0.2):
        """tap a key with a random interval"""
        if len(key) != 1:
            key = self.KEY_DICT[key]

        self.k.press_key(key)
        await self.delay(self.interval)
        self.k.release_key(key)
        await self.delay(self.interval * 0.5)
        if delay:
            await self.delay(delay)

    async def type_string(self, a_string, delay=0.2):
        """type a string to the computer"""
        self.k.type_string(a_string)

        if delay:
            await self.delay(delay)

    async def mouse_pos(self):
        return self.m.position()
