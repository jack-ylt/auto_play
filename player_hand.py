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


m = PyMouse()
k = PyKeyboard()

def distance(p1, p2):
    x = (p1[0] - p2[0]) ** 2
    y = (p1[1] - p2[1]) ** 2
    dist = math.sqrt(x + y)
    return dist

class Hand(object):
    err = 0.05
    interval = 0.04
    during_click = False

    async def _do_click(self, pos):
        """avoid do mouse click at the same time."""
        try:
            for _ in range(10):
                if not self.during_click:
                    self.during_click = True
                    # 点击，有时候会没反应
                    # m.click(*pos)
                    m.press(*pos)
                    await asyncio.sleep(0.1)
                    m.release(*pos)
                    self.during_click = False
                    return 
                await asyncio.sleep(0.1)
            else:
                logger.warning(f"too busy to do click at {pos}")
        except asyncio.CancelledError:
            logger.debug("_do_click cancelled")
            raise
        finally:
            self.during_click = False

    async def delay(self, n):
        """delay n seconds, with a random +- err error."""
        random_err = (-n + 2*n*random.random()) * self.err
        await asyncio.sleep(n + random_err)
    
    async def click(self, pos, n=1, delay=1, cheat=True, fdelay=0):
        """simulate a player to do a left-click"""
        # if fdelay:
        #     sleep(0.03)   # make shure not click at the same time
        if cheat:
            x = pos[0] + random.randint(-10, 10)
            y = pos[1] + random.randint(-5, 5)
        else:
            x, y = pos

        for _ in range(n):
            await self._do_click((x, y))
            await asyncio.sleep(0.2)

        logger.debug(f"click {pos} {n} times")
        if delay:
            await self.delay(delay)    # the game need some time to response for the click
        
    async def drag(self, p1, p2, t = 0.2):
        """drag from position 1 to position 2"""
        x = p1[0]
        y = p1[1]
        m.press(x, y)
        step = 10
        while distance((x, y), p2) >= 1 :
            x += (p2[0] - x)/step
            y += (p2[1] - y)/step
            step -= 1
            m.move(int(x), int(y))
            await asyncio.sleep(0.02)
        m.release(p2[0], p2[1])
        await asyncio.sleep(t)
        logger.debug(f"drag from {p1} to {p2}")

    async def scroll(self, vertical_num, delay=0.5):
        """垂直滚动"""
        num = vertical_num
        if num > 0:
            while num > 0:
                num -= 1
                m.scroll(1)
                await asyncio.sleep(0.1)
        elif num < 0:
            while num < 0:
                num += 1
                m.scroll(-1)
                await asyncio.sleep(0.1)
        else:
            if delay:
                await self.delay(delay)
            if vertical_num < 0:
                logger.debug(f"scroll down {vertical_num}")
            else:
                logger.debug(f"scroll up {vertical_num}")

    async def move(self, x, y, delay=0.5):
        m.move(x, y)
        if delay:
            await self.delay(delay)
        
    async def tap_key(self, key, n=1, delay=0.033):
        """tap a key with a random interval"""
        for _ in range(n):
            k.press_key(key)
            await self.delay(self.interval)
            k.release_key(key)
            await self.delay(self.interval * 0.5)
        logger.debug(f"tap_key {key} {n} times")
        if delay:
            await self.delay(delay)

    async def type_string(self, a_string, delay=0.033):
        """type a string to the computer"""
        k.type_string(a_string)
        logger.debug(f"type_string {a_string}")
        if delay:
            await self.delay(delay)

def log():
    print('handler.py')
    logger.info('logged from lib module')
    