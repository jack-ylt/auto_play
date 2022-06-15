"""
用于启动模拟器
"""

import asyncio
from lib.player import FindTimeout
from lib.windows import Window
import time


class Emulator(object):
    def __init__(self, player):
        self.player = player
        self.window_list = [Window(i)
                            for i in ['left_top', 'left_down', 'right_top']]

    async def start_all_emulator(self):
        """start all emulator and yield the started window
        """
        # emulator alread started
        pos_list = await self.player.find_all_pos('emulator_ok')
        if pos_list:
            for pos in pos_list:
                yield self._in_which_window(pos)
        else:
            await self. _start_emulator()
            await asyncio.sleep(20)
            pos_list = await self.player.find_all_pos('ye_sheng')
            win_list = list(map(self._in_which_window, pos_list))
            while win_list:
                # await asyncio.sleep(5)
                time.sleep(3)
                _, pos = await self.player.monitor('emulator_started', timeout=60)
                win = self._in_which_window(pos)
                # 可能会重复find同一个emulator_started
                if win in win_list:
                    win_list.remove(win)
                    yield win

    def _in_which_window(self, pos):
        for win in self.window_list:
            if win.in_window(pos):
                return win
        msg = "can't find the {pos} on which window."
        self.player.logger.warning(msg)
        self.player.save_operation_pics(msg)
        return None

    async def _start_emulator(self):
        try:
            _, pos = await self.player.monitor('emulator_icon')
        except FindTimeout:
            msg = "Start emulator failed: can't find the emulator_icon"
            self.player.logger.info(msg)
            self.player.save_operation_pics(msg)
            return False

        await self.player.double_click(pos)
        await self.player.find_then_click('duo_kai_guang_li')
        await self.player.find_then_click('select_all')

        try:
            await self.player.monitor('selected', timeout=2)
        except FindTimeout:
            await self.player.find_then_click('select_all')

        await self.player.find_then_click('start_emulator', threshold=0.9)
