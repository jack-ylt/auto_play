from lib.ui_data import POS_DICT, WINDOW_DICT, WIDTH, HIGH, CLOSE_BUTTONS, OK_BUTTONS
from lib import player_hand
from lib import player_eye
import asyncio
import logging
import queue
import functools
import time
import os
from datetime import datetime
logger = logging.getLogger(__name__)


FindTimeout = player_eye.FindTimeout


def _get_first(lst):
    return lst[0]


class Player(object):
    def __init__(self, window_name=None, g_queue=None, g_event=None, g_found=None, g_player_lock=None):
        self.window_name = window_name
        if window_name:
            # ImageGrab.grab(bbox=(left, top, right, bottom))
            left, top = WINDOW_DICT[window_name]
            right, bottom = left + WIDTH, top + HIGH
            self.bbox = (left, top, right, bottom)
        else:
            self.bbox = (0, 0, 1920, 1080)
        self.g_queue = g_queue
        self.g_event = g_event
        self.g_found = g_found
        self.g_player_lock = g_player_lock

        self.eye = player_eye.Eye()
        self.hand = player_hand.Hand()

        self.log_queue = queue.Queue(20)

    def _cache_operation_pic(self, msg, pos=None, new=True, ext=".jpg"):
        msg = msg.replace(', ', ',').replace(':', '-').replace(' ', '-')
        now = datetime.now().strftime('%H-%M-%S,%f')[:-3]
        name = now + '_' + msg + ext
        img = self.eye.get_lates_screen(area=self.bbox, new=new)
        if pos:
            if isinstance(pos, tuple):
                img = self.eye.draw_point(img, pos)
            elif isinstance(pos, list):
                # pos is pos_list
                for p in pos:
                    img = self.eye.draw_point(img, p)
        if self.log_queue.full():
            _ = self.log_queue.get()
            # self.save_operation_pics()
        self.log_queue.put((name, img))

    def save_operation_pics(self, dir):
        while not self.log_queue.empty():
            name, img = self.log_queue.get()
            pic_path = os.path.join(dir, name)
            self.eye.save_picture(img, pic_path)

        # 保存以下最新的屏幕截图
        img = self.eye.get_lates_screen(area=self.bbox, new=True)
        now = datetime.now().strftime('%H-%M-%S,%f')[:-3]
        name = now + '_' + 'last_screen.jpg'
        pic_path = os.path.join(dir, name)
        self.eye.save_picture(img, pic_path)


    def real_pos(self, pos):
        x, y = pos
        dx, dy = WINDOW_DICT[self.window_name]
        return (x + dx, y + dy)

    async def is_disabled_button(self, pos):
        if pos[0] < WIDTH and pos[1] < HIGH:
            pos = self.real_pos(pos)
        return await self.eye.is_gray(pos)

    async def monitor(self, names, timeout=10, threshold=0.8, filter_func=_get_first):
        """return (name, pos), all rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        name, pos_list = await self.eye.monitor(names, area=self.bbox, timeout=timeout, threshold=threshold)
        pos = filter_func(pos_list)
        msg = f"found {name} at {pos}"
        # logger.debug(msg)
        self._cache_operation_pic(msg, pos, new=False)

        return name, pos

    async def find_all_pos(self, names, threshold=0.8):
        """return (name, pos), all rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        pos_list = await self.eye.find_all_pos(names, area=self.bbox, threshold=threshold)
        # 如果没找到，就不要记录了
        if pos_list:
            msg = f"found {names} at {pos_list}"
            # logger.debug(msg)
            self._cache_operation_pic(msg, pos_list, new=False)
        return pos_list


    async def click(self, pos, delay=1, cheat=True):
        await asyncio.sleep(delay / 2)
        pos_copy = pos[:]
        if isinstance(pos, str):
            pos = POS_DICT[pos]

        # click 的 pos 可能来自monitor的实际坐标，也可能是代码中的伪坐标
        if pos[0] < WIDTH and pos[1] < HIGH:
            pos = self.real_pos(pos)

        msg = f"{self.window_name}: click {pos_copy}"
        logger.debug(msg)
        async with self.g_player_lock:
            await self.hand.click(pos, cheat=cheat)
        
        await asyncio.sleep(delay / 2)
        self._cache_operation_pic(msg, pos_copy)

    async def double_click(self, pos, delay=1, cheat=True):
        pos_copy = pos[:]
        if isinstance(pos, str):
            pos = POS_DICT[pos]

        # click 的 pos 可能来自monitor的实际坐标，也可能是代码中的伪坐标
        if pos[0] < WIDTH and pos[1] < HIGH:
            pos = self.real_pos(pos)

        msg = f"{self.window_name}: double-click {pos_copy}"
        logger.debug(msg)
        async with self.g_player_lock:
            await self.hand.double_click(pos, cheat=cheat)
        
        await asyncio.sleep(delay)
        self._cache_operation_pic(msg, pos_copy)

    async def drag(self, p1, p2, speed=0.05, stop=False):
        """drag from position 1 to position 2"""
        msg = f"{self.window_name}: drag from {p1} to {p2}"
        logger.debug(msg)

        p1, p2 = map(self.real_pos, [p1, p2])
        async with self.g_player_lock:
            await self.hand.drag(p1, p2, speed, stop)

        self._cache_operation_pic(msg, [p1, p2])

    async def scroll(self, vertical_num, pos=None, delay=0.2):
        """滚动 家园的楼层地图的时候，容易误操作"""
        if vertical_num < 0:
            msg = f"{self.window_name}: scroll down {vertical_num}"
        else:
            msg = f"{self.window_name}: scroll up {vertical_num}"

        async with self.g_player_lock:
            if pos:
                await self.hand.move(*pos)
            await self.hand.scroll(vertical_num, delay)

        logger.debug(msg)
        self._cache_operation_pic(msg)

    async def move(self, x, y, delay=0.2):
        pos_copy = (x, y)
        x, y = self.real_pos((x, y))
        
        async with self.g_player_lock:
            await self.hand.move(x, y, delay)

        msg = f"{self.window_name}: move to {pos_copy}"
        logger.debug(msg)
        self._cache_operation_pic(msg, pos_copy)

    async def tap_key(self, key, delay=1):
        """tap a key with a random interval"""
        async with self.g_player_lock:
            await self.hand.tap_key(key)

        msg = f"{self.window_name}: tap_key {key}"
        logger.debug(msg)
        
        await asyncio.sleep(delay)
        self._cache_operation_pic(msg)

    def in_window(self, pos):
        min_x, min_y = WINDOW_DICT[self.window_name]
        max_x, max_y = min_x + WIDTH, min_y + HIGH
        return min_x < pos[0] < max_x and min_y < pos[1] < max_y

    async def go_back(self):
        pos_window_border = (400, 8)
        msg = f"{self.window_name}: go_back"
        logger.debug(msg)
        async with self.g_player_lock:
            mouse_pos = await self.hand.mouse_pos()
            if not self.in_window(mouse_pos):
                pos = self.real_pos(pos_window_border)
                await self.hand.click(pos, cheat=False)
                await asyncio.sleep(0.2)
            await self.hand.tap_key('esc')
            
        await asyncio.sleep(1)    # 切换界面需要点时间
        self._cache_operation_pic(msg)


    async def go_back_to(self, pic):
        msg = f"{self.window_name}: go back to {pic}"
        logger.debug(msg)
        # 弹出框的标志要放前面，比如colose和go_back都有，要先close
        pics =  OK_BUTTONS + CLOSE_BUTTONS + [pic] + ['go_back']
        for _ in range(10):
            name, pos = await self.monitor(pics)
            if name == pic:
                return True
            await self.click(pos)
            self._cache_operation_pic(msg)
        
        return False

    async def information_input(self, pos, info):
        """click the input box, then input info"""
        msg = f"{self.window_name}: input '{info}' at {pos}"
        logger.debug(msg)
        
        async with self.g_player_lock:
            if pos[0] < WIDTH and pos[1] < HIGH:
                pos = self.real_pos(pos)
            # await self.hand.click(pos)
            await self.hand.double_click(pos)
            await asyncio.sleep(0.2)
            await self.hand.tap_key('backspace')
            await asyncio.sleep(0.2)
            await self.hand.type_string(info)

        self._cache_operation_pic(msg)

    async def multi_click(self, pos_list, delay=1, cheat=True):
        new_pos_list = []

        for pos in pos_list:
            if isinstance(pos, str):
                pos = POS_DICT[pos]
            if pos[0] < WIDTH and pos[1] < HIGH:
                pos = self.real_pos(pos)
            new_pos_list.append(pos)

        msg = f"{self.window_name}: multi click {new_pos_list}"
        logger.debug(msg)
        async with self.g_player_lock:
            for pos in new_pos_list:
                await self.hand.click(pos, cheat=cheat)
                await asyncio.sleep(0.2)
            await asyncio.sleep(0.1)

        await asyncio.sleep(delay)
        self._cache_operation_pic(msg, pos_list)

    async def find_then_click(self, name_list, pos=None, threshold=0.7, timeout=10, delay=1, raise_exception=True, cheat=True):
        """find a image, then click it ant return its name

        if pos given, click the pos instead.
        """
        if not isinstance(name_list, list):
            name_list = [name_list]

        try:
            name, pos_img = await self.monitor(name_list, threshold=threshold, timeout=timeout)
        except FindTimeout:
            if raise_exception:
                raise
            else:
                return None
        if not pos:
            pos = pos_img

        await self.click(pos, delay=delay, cheat=cheat)

        return name

    async def type_string(self, a_string, delay=1):
        """type a string to the computer"""
        msg = f"{self.window_name}: type_string {a_string}"
        logger.debug(msg)
        async with self.g_player_lock:
            await self.hand.type_string(a_string, delay)
        
        await asyncio.sleep(delay)
        self._cache_operation_pic(msg)
