import asyncio
import logging
from lib.player import Player, FindTimeout
from lib.windows import Window



class Emulator(object):
    def __init__(self, player):
        self.player = player

    async def emulator_started(self):
        try:
            await self.player.monitor('ye_sheng', timeout=1)
            return True
        except FindTimeout:
            return False

    async def start_emulator(self):
        try:
            _, pos = await self.player.monitor('emulator_icon')
        except FindTimeout:
            self.player.logger.info("Start emulator failed: can't find the emulator_icon")
            return False

        await self.player.double_click(pos)
        await self.player.find_then_click('duo_kai_guang_li')
        await self.player.find_then_click('select_all')

        try:
            await self.player.monitor('selected', timeout=2)
        except FindTimeout:
            await self.player.find_then_click('select_all')

        await self.player.find_then_click('start_emulator', threshold=0.9)

    async def wait_emulator_started(self, window_list):
        windows = window_list[:]
        while windows:
            # await asyncio.sleep(3)
            _, pos = await self.player.monitor('emulator_started', timeout=60)
            for w in windows:
                if w.in_window(pos):
                    windows.remove(w)
                    yield w


