"""
用于启动模拟器
"""

import asyncio
from lib.player import FindTimeout
from lib.windows import Window
import time
import os
from lib.global_vals import EmulatorNotFound, EmulatorStartupTimeout, EmulatorSetError
import math

def _is_same_pos(p1, p2, offset=3):
    x, y = p1
    x1, y1 = p2
    return math.fabs(x - x1) < offset and math.fabs(y - y1) < offset

class Emulator(object):
    def __init__(self, player):
        self.player = player
        self.window_list = [Window(i)
                            for i in ['left_top', 'left_down', 'right_top']]

    async def start_all_emulator(self):
        """start all emulator and yield the started window
        """
        try:
            # emulator alread started
            startup_complete_flag, _ = await self.player.monitor(['recent_tasks', 'emulator_ok', 'emulator_ok1'], timeout=1, threshold=0.92)
            pos_list = await self.player.find_all_pos(startup_complete_flag)
            if not await self._is_size_and_pos_ok():
                msg = "emulator positon or size not ok"
                self.player.save_operation_pics(msg)
                raise EmulatorSetError(msg)

            for pos in pos_list:
                yield self.in_which_window(pos)
        except FindTimeout:
            await self._start_emulator()

            try:
                await self.player.monitor('liu_lan_qi', timeout=60, threshold=0.9)
            except FindTimeout:
                msg = "start emulator timeout"
                self.player.save_operation_pics(msg)
                raise EmulatorSetError(msg)

            if not await self._is_size_and_pos_ok():
                msg = "emulator positon or size not ok"
                self.player.save_operation_pics(msg)
                raise EmulatorSetError(msg)

            pos_list = await self.player.find_all_pos('ye_sheng')
            win_list = list(map(self.in_which_window, pos_list))

            seen = []
            while True:
                pos_list = await self.player.find_all_pos('liu_lan_qi', threshold=0.9)
                if pos_list:
                    for pos in pos_list:
                        win = self.in_which_window(pos)
                        if win not in seen:
                            seen.append(win)
                            yield self.in_which_window(pos)

                if len(seen) >= len(win_list):
                    break

                await asyncio.sleep(2)
                
    async def _is_size_and_pos_ok(self):
        """检查模拟器各个窗口的大小、位置是否正确"""
        recent_tasks_pos = [(886, 500), (886, 1020), (1792, 500)]
        pos_list1 = await self.player.find_all_pos('recent_tasks')
        for p1 in pos_list1:
            for p2 in recent_tasks_pos:
                if _is_same_pos(p1, p2, offset=8):
                    break
            else:
                return False
        
        set_icon_pos = [(754, 16), (754, 536), (1660, 16)]
        pos_list2 = await self.player.find_all_pos('set_icon')
        for p1 in pos_list2:
            for p2 in set_icon_pos:
                if _is_same_pos(p1, p2, offset=8):
                    break
            else:
                return False

        # if len(pos_list1) != len(pos_list2):
        #     return False

        return True

            
    def in_which_window(self, pos):
        for win in self.window_list:
            if win.in_window(pos):
                return win
        msg = "can't find the {pos} on which window."
        self.player.logger.warning(msg)
        self.player.save_operation_pics(msg)
        return None

    async def _start_emulator(self):
        try:
            _, pos = await self.player.monitor(['emulator_icon', 'emulator_icon1'], timeout=2, threshold=0.9)
            await self.player.double_click(pos)
        except FindTimeout:
            self.player.logger.debug(
                "can't find the emulator icon, try to search its exe file.")
            exe_file = await self._find_emulator()
            if exe_file:
                os.startfile(exe_file)
            else:
                raise EmulatorNotFound("未找到夜神模拟器，请先安装夜神模拟器")

        await self.player.find_then_click(['duo_kai_guang_li', 'duo_kai_guang_li_1'])
        await self.player.find_then_click('select_all', threshold=0.9)

        try:
            await self.player.monitor('selected', timeout=2, threshold=0.9)
        except FindTimeout:
            await self.player.find_then_click('select_all', threshold=0.9)

        await asyncio.sleep(2)    # 点太快，可能有窗口启动不了
        await self.player.find_then_click('start_emulator', threshold=0.9)

    async def _find_emulator(self):
        emulator_name = 'MultiPlayerManager.exe'
        emulator_dir = 'Program Files'

        tasks = []
        for pan in [r'C:\\', r'D:\\', r'E:\\', r'F:\\']:
            task = asyncio.create_task(_find_file(
                pan + emulator_dir, emulator_name))
            tasks.append(task)

        try:
            for coro in asyncio.as_completed(tasks, timeout=5):
                file_path = await coro
                if os.path.isfile(file_path):
                    self.player.logger.debug(
                        f'find the emulator at {file_path}')
                    return file_path
        except asyncio.TimeoutError:
            self.player.logger.debug('timeout, cant find the emulator')
            return ''
        # finally:
        #     group = asyncio.gather(*tasks, return_exceptions=False)
        #     group.cancel()


async def _find_file(start, name):
    if not os.path.isdir(start):
        return ''

    for path, _, files in os.walk(start):
        if name in files:
            full_path = os.path.join(start, path, name)
            full_path = os.path.normpath(os.path.abspath(full_path))
            return full_path
        await asyncio.sleep(0.1)
    return ''
