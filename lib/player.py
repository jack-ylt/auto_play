from lib.ui_data import POS_DICT, WINDOW_DICT, WIDTH, HIGH
from lib import player_hand
from lib import player_eye
import asyncio
import logging
logger = logging.getLogger(__name__)



FindTimeout = player_eye.FindTimeout


class Player(object):
    def __init__(self, window_name, g_queue, g_event, g_found, g_player_lock):
        self.window_name = window_name
        self.g_queue = g_queue
        self.g_event = g_event
        self.g_found = g_found
        self.g_player_lock = g_player_lock

        self.eye = player_eye.Eye()
        self.hand = player_hand.Hand()

    def real_pos(self, pos):
        x, y = pos
        dx, dy = WINDOW_DICT[self.window_name]
        return (x + dx, y + dy)

    async def monitor(self, names, timeout=10, threshold=0.7, filter_func=None):
        """return (name, pos), all rease timeout_error"""
        async def _monitor(window_name):
            while True:
                await self.g_queue.put([window_name, names, threshold])
                await self.g_event.wait()

                for res in self.g_found[window_name]:
                    pic_name, pos_list = res
                    if pos_list:
                        if filter_func:
                            pos = filter_func(pos_list)
                        else:
                            pos = pos_list[0]
                        pos = self.real_pos(pos)
                        logger.debug(f"{window_name} found {pic_name} at {pos}")
                        return (pic_name, pos)

        logger.debug(f'{self.window_name}: start monitor: {names}')
        if not isinstance(names, list):
            names = [names]

        try:
            res = await asyncio.wait_for(_monitor(self.window_name), timeout=timeout)
            return res
        except asyncio.TimeoutError:
            msg = (f"{self.window_name}: monitor {names} timeout. ({timeout} s)")
            raise FindTimeout(msg)

    async def find_all_pos(self, names, threshold=0.8, max_try=1):
        """return list of pos"""
        logger.debug(f'{self.window_name}: start find all positions of: {names}')

        if not isinstance(names, list):
            names = [names]
        all_pos = []

        for _ in range(max_try):
            await self.g_queue.put([self.window_name, names, threshold])

            while True:
                await self.g_event.wait()
                # 确保得到了查找结果
                if self.g_found[self.window_name]:
                    break

            for res in self.g_found[self.window_name]:
                _, pos_list = res
                if pos_list:
                    all_pos.extend(pos_list)

            if all_pos:
                break    # 找到了就退出， 否则，就多尝试几次
            else:
                await asyncio.sleep(1)

        # 多个pic的情况下，可能会有重合
        all_pos = player_eye.de_duplication(all_pos)
        all_pos.sort()
        all_pos = list(map(self.real_pos, all_pos))
        if all_pos:
            logger.debug(f'{self.window_name}: find_all_pos of {names} at {all_pos}')
        else:
            logger.debug(f'{self.window_name}: no find any pos of {names}')

        return all_pos

    async def find_text_pos(self, text, threshold=0.8):
        """return a pos"""
        logger.debug(f'{self.window_name}: start find pos of: {text}')

        pos = self.eye.find_text_pos(text, self.window_name)

        if pos == (-1, -1):
            logger.debug(f'{self.window_name}: no find the pos of {text}')
        else:
            pos = self.real_pos(pos)
            logger.debug(f'{self.window_name}: find text pos of {text} at {pos}')

        return pos


    async def click(self, pos, delay=1, cheat=True):
        if isinstance(pos, str):
            pos = POS_DICT[pos]

        # click 的 pos 可能来自monitor的实际坐标，也可能是代码中的伪坐标
        if pos[0] < WIDTH and pos[1] < HIGH:
            pos = self.real_pos(pos)

        logger.debug(f"{self.window_name}: click {pos}")
        async with self.g_player_lock:
            await self.hand.click(pos, cheat=cheat)
        await asyncio.sleep(delay)
        
    async def double_click(self, pos, delay=1, cheat=True):
        if isinstance(pos, str):
            pos = POS_DICT[pos]

        # click 的 pos 可能来自monitor的实际坐标，也可能是代码中的伪坐标
        if pos[0] < WIDTH and pos[1] < HIGH:
            pos = self.real_pos(pos)

        logger.debug(f"{self.window_name}: double-click {pos}")
        async with self.g_player_lock:
            await self.hand.double_click(pos, cheat=cheat)
        await asyncio.sleep(delay)

    async def drag(self, p1, p2, speed=0.05, delay=0.2):
        """drag from position 1 to position 2"""
        p1, p2 = map(self.real_pos, [p1, p2])
        logger.debug(f"{self.window_name}: drag from {p1} to {p2}")
        async with self.g_player_lock:
            await self.hand.drag(p1, p2, speed, delay)

    async def scroll(self, vertical_num, delay=0.2):
        if vertical_num < 0:
            logger.debug(f"{self.window_name}: scroll down {vertical_num}")
        else:
            logger.debug(f"{self.window_name}: scroll up {vertical_num}")
        async with self.g_player_lock:
            await self.hand.scroll(vertical_num, delay)

    async def move(self, x, y, delay=0.2):
        x, y = self.real_pos((x, y))
        logger.debug(f"{self.window_name}: move to ({x}, {y})")
        async with self.g_player_lock:
            await self.hand.move(x, y, delay)

    async def tap_key(self, key, delay=1):
        """tap a key with a random interval"""
        logger.debug(f"{self.window_name}: tap_key {key}")
        async with self.g_player_lock:
            await self.hand.tap_key(key)
        await asyncio.sleep(delay)

    def in_window(self, pos):
        min_x, min_y = WINDOW_DICT[self.window_name]
        max_x, max_y = min_x + WIDTH, min_y + HIGH
        return min_x < pos[0] < max_x and min_y < pos[1] < max_y

    async def go_back(self):
        pos_window_border = (400, 8)
        logger.debug(f"{self.window_name}: go_back")
        async with self.g_player_lock:
            mouse_pos = await self.hand.mouse_pos()
            if not self.in_window(mouse_pos):
                pos = self.real_pos(pos_window_border)
                await self.hand.click(pos, cheat=False)
                await asyncio.sleep(0.2)
            await self.hand.tap_key('esc')
        await asyncio.sleep(1)    # 切换界面需要点时间

    async def information_input(self, pos, info):
        """click the input box, then input info"""
        logger.debug(f"{self.window_name}: input '{info}' at {pos}")
        async with self.g_player_lock:
            if pos[0] < WIDTH and pos[1] < HIGH:
                pos = self.real_pos(pos)
            # await self.hand.click(pos)
            await self.hand.double_click(pos)
            await asyncio.sleep(0.2)
            await self.hand.tap_key('backspace')
            await asyncio.sleep(0.2)
            await self.hand.type_string(info)

    async def multi_click(self, pos_list, delay=1, cheat=True):
        new_pos_list = []
        
        for pos in pos_list:
            if isinstance(pos, str):
                pos = POS_DICT[pos]
            if pos[0] < WIDTH and pos[1] < HIGH:
                pos = self.real_pos(pos)
            new_pos_list.append(pos)

        logger.debug(f"{self.window_name}: multi click {new_pos_list}")
        async with self.g_player_lock:
            for pos in new_pos_list:
                await self.hand.click(pos, cheat=cheat)
                await asyncio.sleep(0.2)
            await asyncio.sleep(0.2)

        await asyncio.sleep(delay)

    async def find_then_click(self, name_list, pos=None, threshold=0.7, timeout=10, raise_exception=True, cheat=True):
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
        if pos:
            await self.click(pos, cheat=cheat)
        else:
            await self.click(pos_img, cheat=cheat)
        return name


 

    async def type_string(self, a_string, delay=1):
        """type a string to the computer"""
        logger.debug(f"{self.window_name}: type_string {a_string}")
        async with self.g_player_lock:
            await self.hand.type_string(a_string, delay)
        await asyncio.sleep(delay)
