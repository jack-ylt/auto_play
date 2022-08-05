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
import pyautogui
import logging
from lib.global_vals import MouseFailure

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
        'ctrl': k.control_key,
    }

    def __init__(self, my_logger=None):
        if my_logger:
            self.logger = my_logger
        else:
            self.logger = logger

    async def delay(self, n):
        """delay n seconds, with a random +- err error."""
        random_err = (-n + 2*n*random.random()) * self.err
        await asyncio.sleep(n + random_err)

    def click(self, pos, cheat=True):
        """simulate a player to do a left-click"""
        if cheat:
            x = pos[0] + random.randint(-10, 10)
            y = pos[1] + random.randint(-8, 8)
        else:
            x = pos[0] + random.randint(-2, 2)
            y = pos[1] + random.randint(-2, 2)

        # # click 有可能失灵 （大概万分之一）, 先release就能保证click有效了

        pyautogui.moveTo(x, y, duration=0.1, tween=pyautogui.easeInOutQuad)
        pyautogui.click(x, y)

        mouse_pos = self.mouse_pos()
        if mouse_pos != (x, y):
            self.logger.error(
                f"The mouse is failure: want click pos: {(x, y)}, but real mouse pos: {mouse_pos}")
            sleep(5)
            self.m.release(x, y)
            self.m.move(x, y)
            self.m.click(x, y)

            if mouse_pos != (x, y):
                self.logger.error(
                    f"The mouse still failure: want click pos: {(x, y)}, but real mouse pos: {mouse_pos}")
                raise MouseFailure()

    async def double_click(self, pos, cheat=True):
        """simulate a player to do a double left-click"""
        if cheat:
            x = pos[0] + random.randint(-12, 12)
            y = pos[1] + random.randint(-8, 8)
        else:
            x = pos[0] + random.randint(-3, 3)
            y = pos[1] + random.randint(-2, 2)

        self.m.click(x, y, 1, 2)
        # self.m.click(x, y)
        await asyncio.sleep(0.1)

    async def drag(self, p1, p2, speed=0.05, stop=False):
        """drag from position 1 to position 2"""
        x1 = p1[0] + random.randint(-5, 5)
        y1 = p1[1] + random.randint(-3, 3)
        x2 = p2[0] + random.randint(-5, 5)
        y2 = p2[1] + random.randint(-3, 3)
        step = 10

        self.m.move(x1, y1)
        self.m.press(x1, y1)

        while distance((x1, y1), (x2, y2)) >= 1:
            x1 += int((x2 - x1)/step)
            y1 += int((y2 - y1)/step)
            step -= 1
            self.m.move(x1, y1)
            await asyncio.sleep(speed)

        self.m.move(x2, y2)
        if stop:
            await asyncio.sleep(0.6)
        else:
            await asyncio.sleep(0.1)
        self.m.release(x2, y2)
        await asyncio.sleep(0.3)

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

    async def press_key(self, key):
        if len(key) != 1:
            key = self.KEY_DICT[key]
        self.k.press_key(key)

    async def release_key(self, key):
        if len(key) != 1:
            key = self.KEY_DICT[key]
        self.k.release_key(key)

    async def type_string(self, a_string, delay=0.2):
        """type a string to the computer"""
        self.k.type_string(a_string)

        if delay:
            await self.delay(delay)

    def mouse_pos(self):
        return self.m.position()
