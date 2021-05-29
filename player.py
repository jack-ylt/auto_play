from ui_data import POS_DICT
import player_hand
import player_eye
import asyncio
from auto_play import filter_bottom
from global_val import g_queue, g_event, g_found, g_player_lock
from ui_data import WINDOW_DICT, WIDTH, HIGH
import logging
logger = logging.getLogger(__name__)


class FindTimeout(Exception):
    """
    when no found and timeout, raise 
    """
    pass


class Player(object):
    def __init__(self, window_name):
        self.window_name = window_name
        self.eye = player_eye.Eye()
        self.hand = player_hand.Hand()

    def real_pos(self, pos):
        x, y = pos
        dx, dy = WINDOW_DICT[self.window_name]
        return (x + dx, y + dy)

    async def monitor(self, names, timeout=5, threshold=0.8, filter_func=None):
        """return (name, pos), all rease timeout_error"""
        async def _monitor(window_name):
            while True:
                g_queue.put([window_name, names, threshold])

                await g_event.wait()

                for res in g_found[window_name]:
                    pic_name, pos_list = res
                    if pos_list:
                        if filter_func:
                            pos = filter_func(pos_list)
                        else:
                            pos = pos_list[0]
                        pos = self.real_pos(pos)
                        logger.debug(f'found {pic_name} at {pos}')
                        return (pic_name, pos)

        logger.debug(f'start monitor: {names}')
        try:
            res = await asyncio.wait_for(_monitor(self.window_name), timeout=timeout)
            return res
        except asyncio.TimeoutError:
            msg = (f"monitor {names} timeout. ({timeout} s)")
            raise FindTimeout(msg)

    async def find_all_pos(self, names, threshold=0.8):
        """return list of pos"""
        logger.debug(f'start find all positions of: {names}')

        all_pos = []

        g_queue.put([self.window_name, names, threshold])

        while True:
            await g_event.wait()
            # 确保得到了查找结果
            if g_found[self.window_name]:
                break

        for res in g_found[self.window_name]:
            _, pos_list = res
            if pos_list:
                all_pos.extend(pos_list)

        # 多个pic的情况下，可能会有重合
        all_pos = player_eye.de_duplication(all_pos)
        all_pos.sort()
        all_pos = map(self.real_pos, all_pos)
        if all_pos:
            logger.debug(f'find_all_pos of {names} at {all_pos}')
        else:
            logger.debug(f'no find any pos of {names}')

        return all_pos

    async def click(self, pos):
        if isinstance(pos, str):
            pos = POS_DICT[pos]

        pos = self.real_pos(pos)
        await self.hand.click(pos)

    async def drag(self, p1, p2, delay=0.2):
        """drag from position 1 to position 2"""
        p1, p2 = map(self.real_pos, [p1, p2])
        await self.hand.drag(p1, p2, delay)

    async def scroll(self, vertical_num, delay=0.5):
        await self.hand.scroll(vertical_num, delay)

    async def move(self, x, y, delay=0.5):
        x, y = self.real_pos((x, y))
        await self.hand.move(x, y, delay)

    async def tap_key(self, key, delay=0.2):
        """tap a key with a random interval"""
        await self.hand.tap_key(key, delay)

    def in_window(self, pos):
        min_x, min_y = WINDOW_DICT[self.window_name]
        max_x, max_y = min_x + WIDTH, min_y + HIGH
        return min_x < pos[0] < max_x and min_y < pos[1] < max_y

    async def go_back(self):
        mouse_pos = self.hand.mouse_pos()
        if not self.in_window(mouse_pos):
            async with g_player_lock:
                await self.hand.move(200, 200)
                await self.hand.tap_key('esc')
        else:
            await self.hand.tap_key('esc')

    async def type_string(self, a_string, delay=0.2):
        """type a string to the computer"""
        await self.hand.type_string(a_string, delay)
