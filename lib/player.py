from lib.ui_data import POS_DICT, WINDOW_DICT, WIDTH, HIGH, CLOSE_BUTTONS, OK_BUTTONS
from lib import player_hand
from lib import player_eye
import asyncio
# import logging
import queue
# import functools
import time
import os
from datetime import datetime
import random
import re
from lib.helper import change_language
from lib.mylogs import make_logger
# from lib.read_cfg import read_role_cfg
# from lib.recorder import PlayCounter
from collections import defaultdict
import pyperclip

FindTimeout = player_eye.FindTimeout


def _get_first(lst):
    return lst[0]

def _top_match(lst):
    pass

def _random_offset(pos, dx=10, dy=8):
    x = pos[0] + random.randint(-dx, dx)
    y = pos[1] + random.randint(-dy, dy)
    return (x, y)


class Player(object):
    def __init__(self, g_lock=None, g_sem=None, window=None, logger=None):
        self.g_lock = g_lock
        self.g_sem = g_sem
        self.window = window
        if logger is None:
            self.logger = make_logger(self.window.name)
        else:
            self.logger = logger

        self.eye = player_eye.Eye(self.logger)
        self.hand = player_hand.Hand(self.logger)
        self.log_queue = queue.Queue(10)
        self.last_click = None

    def _cache_operation_pic(self, msg, pos=None, new=True, ext=".jpg"):
        msg = re.sub(r'[^a-zA-Z0-9-_]', ' ', msg)
        msg = re.sub(r'\s+', ' ', msg)
        now = datetime.now().strftime('%H-%M-%S-%f')[:-3]
        time_str = now.replace('-', ':')[:-5]    # 截掉个位秒以后的值，避免取不到日志
        name = msg[:50] + ext
        img = self.eye.get_lates_screen(area=self.window.bbox, new=new)
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

        self.log_queue.put((time_str, name, img))

    def save_operation_pics(self, msg):
        now = datetime.now().strftime('%H-%M-%S-%f')[:-3]
        msg = re.sub(r'[^a-zA-Z0-9-_]', ' ', msg)
        msg = re.sub(r'\s+', ' ', msg)
        dir_name = msg[:50] + ' ' + now
        # dir_path = os.path.join('./timeout_pics', dir_name)
        dir_path = os.path.join('logs', dir_name)
        os.makedirs(dir_path)

        # TODO 这个实现比较粗糙
        time_str, name, img = self.log_queue.get()
        pic_path = os.path.join(dir_path, '0 ' + name)
        self.eye.save_picture(img, pic_path)

        today = datetime.now().strftime(r'%Y-%m-%d')
        src_log = os.path.join('logs', self.window.name + '_' + today + '.log')
        dst_log = os.path.join(dir_path, 'log.log')
        self.extract_log_text(src_log, time_str, dst_log)

        lst = []
        idx = 1
        while not self.log_queue.empty():
            time_str, name, img = self.log_queue.get()
            lst.append((time_str, name, img))
            pic_path = os.path.join(dir_path, str(idx) + ' ' + name)
            self.eye.save_picture(img, pic_path)
            idx += 1

        # 可能下次保持还能用上
        for i in lst:
            self.log_queue.put(i)

        # 保存一下最新的屏幕截图
        img = self.eye.get_lates_screen(area=self.window.bbox, new=True)
        name = 'last_screen.jpg'
        pic_path = os.path.join(dir_path, name)
        self.eye.save_picture(img, pic_path)

    def extract_log_text(self, src_log, time_str, dst_log):
        lines = []

        with open(src_log) as f:
            tag = False
            for line in f:
                if tag:
                    lines.append(line)
                else:
                    if time_str in line:
                        tag = True
                        lines.append(line)

        with open(dst_log, 'w') as f:
            f.write(''.join(lines))

    async def is_disabled_button(self, pos):
        pos = self.window.real_pos(pos)

        # 灰色按钮有少量像素不是灰色的, 需要多判断几个点
        for _ in range(3):
            nearby_pos = _random_offset(pos)
            if await self.eye.is_gray(nearby_pos):
                return True
        return False

    async def monitor(self, names, timeout=15, threshold=0.8, filter_func=_get_first, verify=False, interval=0.5):
        """return (name, pos), all rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        name, pos_list = await self.eye.monitor(names, area=self.window.bbox, timeout=timeout, threshold=threshold, verify=verify, interval=interval)

        pos = filter_func(pos_list)
        msg = f"find {name} at {pos}"
        self._cache_operation_pic(msg, pos, new=False)

        # 如果找到了，清空latest_operation，防止错误re-click
        self.last_click = None
        return name, pos

    def is_exist(self, names, threshold=0.8):
        return self.eye.is_exist(names, area=self.window.bbox, threshold=threshold)


    async def find_all_pos(self, names, threshold=0.8):
        """return pos_list, all rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        pos_list = await self.eye.find_all_pos(names, area=self.window.bbox, threshold=threshold)
        # 如果没找到，就不要记录了
        if pos_list:
            msg = f"find {names} at {pos_list}"
            # self.logger.debug(msg)
            self._cache_operation_pic(msg, pos_list, new=False)
        return pos_list
    
    async def find_all_name(self, names, threshold=0.8):
        """return name_list, all rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        d = await self.eye.find_all_name_pos(names, area=self.window.bbox, threshold=threshold)
        name_list = d.keys()
        pos_list = []
        for k, v in d.items():
            pos_list.extend(v)
        # 如果没找到，就不要记录了
        if name_list:
            msg = f"find {name_list} at {pos_list}"
            # self.logger.debug(msg)
            self._cache_operation_pic(msg, pos_list, new=False)

        return name_list
    

    async def find_combo(self, target_names, verify_names, dx=(-500, 500), dy=(-500, 500), ret='name'):
        def _is_close(p1, p2):
            x1, y1 = p1
            x2, y2 = p2
            if dx[0] < x1 - x2 < dx[1] and dy[0] <= y1 - y2 <= dy[1]:
                return True
            return False
        
        if not isinstance(target_names, list):
            target_names = [target_names]
        if not isinstance(verify_names, list):
            verify_names = [verify_names]

        d1 = await self.eye.find_all_name_pos(target_names, area=self.window.bbox)
        verify_pos_lst = await self.find_all_pos(verify_names)

        d2 = defaultdict(list)
        for name, pos_lst in d1.items():
            for p1 in pos_lst:
                for p2 in verify_pos_lst:
                    if _is_close(p1, p2):
                        d2[name].append(p1)
        if ret == 'name':
            return d2.keys()
        elif ret == 'pos':
            all_pos = []
            for lst in d2.values():
                all_pos.extend(lst)
            return sorted(self.eye._de_duplication(all_pos))
        else:
            return d2


    async def _verify_click(self, pos):
        start_t = time.time()
        poses = [_random_offset(pos) for i in range(2)]
        pos_colors1 = [await self.eye.get_pos_color(p) for p in poses]
        for _ in range(5):
            await asyncio.sleep(0.2)
            pos_colors2 = [await self.eye.get_pos_color(p) for p in poses]
            if pos_colors1 != pos_colors2:
                end_t = time.time()
                self.logger.debug("_verify_click: pass, {0} != {1}, cost {2}".format(
                    pos_colors1, pos_colors2, end_t - start_t))
                return True
        self.logger.warning("_verify_click not pass")
        return False

    async def click(self, pos, delay=1, cheat=True):

        if isinstance(pos, str):
            pos = POS_DICT[pos]

        pos = self.window.real_pos(pos)
        
        async with self.g_lock:
            try:
                self.hand.click(pos, cheat=cheat) 
            finally:
                mouse_pos = self.hand.mouse_pos()
                msg = f"click {pos}, real mouse pos: {mouse_pos}"
                self.logger.debug(msg)
                win_pos = self.window.win_pos(mouse_pos)
                self._cache_operation_pic(msg, win_pos)

            await asyncio.sleep(0.1)

        await asyncio.sleep(delay / 2)

    def click2(self, pos, cheat=True):
        """不用协程，可以不用锁，让代码顺序执行"""
        if isinstance(pos, str):
            pos = POS_DICT[pos]
        pos = self.window.real_pos(pos)

        self.hand.click(pos, cheat=cheat)
        time.sleep(0.05)

        mouse_pos = self.hand.mouse_pos()
        win_pos = self.window.win_pos(mouse_pos)
        msg = f"click {pos}"
        self.logger.debug(msg)
        self._cache_operation_pic(msg, win_pos)

    async def double_click(self, pos, delay=1, cheat=True):
        pos_copy = pos[:]
        if isinstance(pos, str):
            pos = POS_DICT[pos]

        # click 的 pos 可能来自monitor的实际坐标，也可能是代码中的伪坐标
        if pos[0] < WIDTH and pos[1] < HIGH:
            pos = self.window.real_pos(pos)

        msg = f"{self.window.name}: double-click {pos_copy}"
        self.logger.debug(msg)
        async with self.g_lock:
            await self.hand.double_click(pos, cheat=cheat)
            mouse_pos = self.hand.mouse_pos()
            win_pos = self.window.win_pos(mouse_pos)
            self._cache_operation_pic(msg, win_pos)

        await asyncio.sleep(delay)
        

    async def drag(self, p1, p2, speed=0.05, stop=False, step=10):
        """drag from position 1 to position 2"""
        msg = f"{self.window.name}: drag from {p1} to {p2}"
        self.logger.debug(msg)

        p1, p2 = map(self.window.real_pos, [p1, p2])
        async with self.g_lock:
            await self.hand.drag(p1, p2, speed, stop, step)
            pos1, pos2 = self.window.win_pos(p1), self.window.win_pos(p2)
            self._cache_operation_pic(msg, [pos1, pos2])

    async def drag_then_find(self, p1, p2, pic):
        """drag to p2, then check is pic appear"""
        msg = f"{self.window.name}: drag from {p1} to {p2}"
        self.logger.debug(msg)

        p1, p2 = map(self.window.real_pos, [p1, p2])
        async with self.g_lock:
            await self.hand.drag_and_keep(p1, p2)
            pos1, pos2 = self.window.win_pos(p1), self.window.win_pos(p2)
            self._cache_operation_pic(msg, [pos1, pos2])
            res = self.eye.is_exist(pic, area=self.window.bbox)
            await self.hand.release_mouse(p2)

        return res

    async def scroll(self, vertical_num, pos=None, delay=0.2):
        """滚动 家园的楼层地图的时候，容易误操作"""
        if vertical_num < 0:
            msg = f"{self.window.name}: scroll down {vertical_num}"
        else:
            msg = f"{self.window.name}: scroll up {vertical_num}"

        async with self.g_lock:
            await self._make_window_active()
            if pos:
                await self.hand.move(*pos)
            await self.hand.scroll(vertical_num, delay)

        self.logger.debug(msg)
        self._cache_operation_pic(msg)

    async def move(self, x, y, delay=0.2):
        pos_copy = (x, y)
        x, y = self.window.real_pos((x, y))

        async with self.g_lock:
            await self.hand.move(x, y, delay)

        msg = f"{self.window.name}: move to {pos_copy}"
        self.logger.debug(msg)
        self._cache_operation_pic(msg, pos_copy)

    async def tap_key(self, key, delay=1):
        """tap a key with a random interval"""
        async with self.g_lock:
            await self.hand.tap_key(key)

        msg = f"{self.window.name}: tap_key {key}"
        self.logger.debug(msg)

        await asyncio.sleep(delay)
        self._cache_operation_pic(msg)

    async def go_back(self):
        msg = f"{self.window.name}: go_back via esc"
        self.logger.debug(msg)
        async with self.g_lock:
            await self._make_window_active()
            await self.hand.tap_key('esc')
            self._cache_operation_pic(msg)

        await asyncio.sleep(1)    # 切换界面需要点时间
        

    async def go_back_to(self, pic):
        msg = f"{self.window.name}: go back to {pic}"
        self.logger.debug(msg)
        # 弹出框的标志要放前面，比如colose和go_back都有，要先close
        pics = OK_BUTTONS + CLOSE_BUTTONS + ['go_back', 'go_back1', 'go_back2']
        for _ in range(5):
            try:
                await self.monitor(pic, timeout=2)
                return True
            except FindTimeout:
                try:
                    await self.find_then_click(pics, timeout=1)
                except FindTimeout:
                    # 使用 esc 作为辅助来 go back
                    await self.go_back()

        return False

    async def information_input(self, pos, info, double_click=True):
        """click the input box, then input info"""
        msg = f"{self.window.name}: input '{info}' at {pos}"
        self.logger.debug(msg)

        async with self.g_lock:
            # copy
            pyperclip.copy(info)

            pos = self.window.real_pos(pos)
            if double_click:
                await self.hand.double_click(pos)
            else:
                self.hand.click(pos)
            await asyncio.sleep(0.3)
            await self.hand.tap_key('backspace')
            await asyncio.sleep(0.1)

            # paste
            await self.ctrl_v()

        self._cache_operation_pic(msg)

    async def ctrl_c(self):
        """ctrl-c, 必须要g_lock中调用"""
        await self.hand.press_key('ctrl')
        await asyncio.sleep(0.1)    # 避免copy失败
        await self.hand.tap_key('c')
        await asyncio.sleep(0.1)    # 避免copy失败
        await self.hand.release_key('ctrl')
        await asyncio.sleep(0.3)


    async def ctrl_v(self):
        """ctrl-v, 必须要g_lock中调用"""
        await self.hand.press_key('ctrl')
        await asyncio.sleep(0.1)    # 避免粘贴失败
        await self.hand.tap_key('v')
        await asyncio.sleep(0.1)    # 避免粘贴失败
        await self.hand.release_key('ctrl')
        await asyncio.sleep(0.3)

    async def multi_click(self, pos_list, delay=1, cheat=True):
        new_pos_list = []

        for pos in pos_list:
            if isinstance(pos, str):
                pos = POS_DICT[pos]
            if pos[0] < WIDTH and pos[1] < HIGH:
                pos = self.window.real_pos(pos)
            new_pos_list.append(pos)

        msg = f"{self.window.name}: multi click {new_pos_list}"
        self.logger.debug(msg)
        async with self.g_lock:
            for pos in new_pos_list:
                self.hand.click(pos, cheat=cheat)
                await asyncio.sleep(0.5)

        await asyncio.sleep(delay)
        self._cache_operation_pic(msg, pos_list)

    # 防止误点击到运动目标，所以verify默认True，monitor通常用于监控目标是否出现，因此默认verify是False
    async def find_then_click(self, name_list, pos=None, threshold=0.8, timeout=15, delay=1, raise_exception=True, cheat=True, verify=True, interval=0.5):
        """find a image, then click it ant return its name

        if pos given, click the pos instead.
        """
        if not isinstance(name_list, list):
            name_list = [name_list]

        try:
            name, pos_img = await self.monitor(name_list, threshold=threshold, timeout=timeout, verify=verify, interval=interval)
        except FindTimeout:
            if raise_exception:
                raise
            else:
                return None
        if not pos:
            pos = pos_img

        await self.click(pos, delay=delay, cheat=cheat)

        return name

    # async def type_string(self, a_string, delay=1):
    #     """type a string to the computer"""
    #     msg = f"{self.window.name}: type_string {a_string}"
    #     self.logger.debug(msg)
    #     async with self.g_lock:
    #         await self.hand.type_string(a_string, delay)

    #     await asyncio.sleep(delay)
    #     self._cache_operation_pic(msg)

    async def _make_window_active(self):
        """确保窗口处于激活状态

        主要：必须在 async with self.g_lock 中调用，才能确保效果
        """
        pos_window_border = (400, 8)
        mouse_pos = self.hand.mouse_pos()
        if not self.window.in_window(mouse_pos):
            self.logger.debug(
                f'make windows active, window: {self.window}, mouse: {mouse_pos}')
            pos = self.window.real_pos(pos_window_border)
            self.hand.click(pos, cheat=False)
            await asyncio.sleep(0.1)

    async def scrool_with_ctrl(self, pos, vertical_num=-30):
        self.logger.debug("Raise the horizon")
        async with self.g_lock:
            await self._make_window_active()
            await self.hand.move(*self.window.real_pos(pos))
            await self.hand.press_key('ctrl')
            await self.hand.scroll(vertical_num, 0.2)
            await self.hand.release_key('ctrl')
            await asyncio.sleep(3)

        self._cache_operation_pic('_pull_up_the_lens')

    async def copy_input(self, pos):
        """click the input box, then copy the input info"""
        async with self.g_lock:
            pos = self.window.real_pos(pos)
            await self.hand.double_click(pos)
            _, pos_list = await self.eye.monitor('copy', area=self.window.bbox)
            pos = self.window.real_pos(pos_list[0])
            self.hand.click(pos)
            await asyncio.sleep(0.1)
            text = pyperclip.paste()
        return text
    
    async def get_sui_pian_num(self, pos):
        """获取英雄碎片数量"""
        async with self.g_lock:
            pos = self.window.real_pos(pos)
            self.hand.click(pos)
            await asyncio.sleep(0.3)
            await self.ctrl_c()
            text = pyperclip.paste()

        await self.find_then_click(['que_ding', 'que_ding_L'])
        self.logger.debug(f"get_sui_pian_num: {text}")
        return int(text)
    
    async def set_sui_pian_num(self, pos, num):
        """设定邀请英雄碎片的数量"""
        async with self.g_lock:
            pos = self.window.real_pos(pos)
            self.hand.click(pos)
            await asyncio.sleep(0.3)
            await self.ctrl_c()
            max_num = int(pyperclip.paste())
            input_num = num if max_num > num else max_num
            pyperclip.copy(input_num)
            await asyncio.sleep(0.1)
            await self.ctrl_v()

        await self.find_then_click(['que_ding', 'que_ding_L'])
        self.logger.debug(f"set_sui_pian_num: {input_num}")
        return input_num

    async def wait_disappear(self, name, check_count=5):
        """wait, until the name disappear"""
        for _ in range(check_count):
            if self.is_exist(name):
                await asyncio.sleep(1)
            else:
                return True

        self.logger.warning(
            f"wait {check_count} times, the {name} still not disapper.")
        return False

    async def click_untile_disappear(self, names, max_count=3, threshold=0.8):
        name = await self.find_then_click(names)
        for _ in range(max_count - 1):
            if not self.is_exist(name):
                return True
            try:
                await self.find_then_click(name, timeout=1, threshold=threshold)
                await asyncio.sleep(2)
            except FindTimeout:
                return True
        return False
    
    def get_text(self, area, format=''):
        (x1, y1, x2, y2) = area
        (dx, dy, _, _) = self.window.bbox
        
        real_area = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        text = self.eye.get_text(real_area)
        text = text.strip()    # 删除前后空格
        self.logger.debug(f"get_text: {text}")
        self._cache_operation_pic(f'get_text at {real_area}',  new=False)
        # print('text:', text)

        if format == '':
            return text
        elif format == 'name':
            match_list = re.findall(r'(\w+)', text)
        elif format == 'number':
            match_list = re.findall(r'(\d+)', text)
        else:
            raise TypeError(f"Unkown format {format}")
        
        res = sorted(match_list, key=lambda x: len(x))[-1]

        return res

