# -*-coding:utf-8-*-

##############################################################################
# 主要用于监控游戏屏幕，以及文字识别
#
##############################################################################

from lib.cache import Cacher
from lib.helper import main_dir
import sys
from cv2 import cv2
import re
import numpy as np
from PIL import ImageGrab, Image
import time
from datetime import date, datetime
import os
import asyncio
import math
# from lib.helper import get_window_region
from lib.helper import get_window_region
from lib.ui_data import SCREEN_DICT
from copy import deepcopy
import pyautogui


import logging


logger = logging.getLogger(__name__)

# 不加入系统路径，此文件单独运行，会报错：
# ModuleNotFoundError: No module named 'lib.text_recognition'
# file_dir = os.path.split(os.path.realpath(__file__))[0]
# main_dir = os.path.split(file_dir)[0]
# 打成单文件，只有这个打包前后路径是一致的
# main_dir = os.path.dirname(os.path.realpath(sys.executable))


sys.path.insert(0, main_dir)
pic_dir = os.path.join(main_dir, 'pics')


class FindTimeout(Exception):
    """
    when no found and timeout, raise
    """
    pass


class Eye(object):
    def __init__(self, my_logger=None):
        self.img_dict = {}    # {name: img_obj, ...}
        self.screen_img = None
        if my_logger:
            self.logger = my_logger
        else:
            self.logger = logger
        self._cacher = Cacher()
        self._count = 0

    # def get_lates_screen(self):
    #     return self.screen_img

    def get_lates_screen(self, area=None, new=True):
        if new:
            img = ImageGrab.grab(bbox=area)
            img_np = np.array(img)
            return img_np
        else:
            return self.screen_img

    def save_picture_log(self, msg="", ext=".jpg"):
        img = self.get_lates_screen()
        now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
        name = msg.replace(' ', '_') + '_' + now + ext
        log_path = os.path.join(main_dir, 'logs', 'debug_pics', name)
        cv2.imwrite(log_path, img)

    def draw_point(self, img, pos):
        img_copy = deepcopy(img)
        cv2.circle(img_copy, pos, 5, (0, 0, 250), 1, 4)
        cv2.circle(img_copy, pos, 10, (0, 0, 250), 2, 8)
        return img_copy

    def save_picture(self, img_np, path):
        rgb_img = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        # rgb_img.save(path)
        cv2.imwrite(path, rgb_img)

    async def is_gray(self, pos):
        r, g, b = await self.get_pos_color(pos)
        # rgb相同，且不是纯白或纯黑，认为是灰色
        return r == g == b and 10 < r < 245

    async def get_pos_color(self, pos):
        r, g, b = pyautogui.pixel(*pos)
        return (r, g, b)

    async def find_all_pos(self, names, area=None, threshold=0.8, verify=True):
        """return list of pos"""
        self.logger.debug(
            f'Start to find all positions of: {names}')

        if not isinstance(names, list):
            names = [names]

        all_pos = []

        img_bg = self._screenshot(area=area)
        for name in names:
            img_target = self._get_img(name)
            pos_list, max_val = self._find_img_pos(
                img_bg, img_target, threshold=threshold)
            if pos_list:
                self.logger.debug(
                    f"Found {name} at {pos_list}, max_val: {max_val}")
                if verify:
                    res = await self._verify_monitor(name, pos_list[0], threshold, base_area=area)
                    if not res:
                        continue
                all_pos.extend(pos_list)

        all_pos = sorted(self._de_duplication(all_pos))

        if not all_pos:
            self.logger.debug(f'No find any pos of {names}')

        return all_pos

    async def _verify_monitor(self, name, pos, threshold, base_area):
        """验证图片位置是否还在原地"""
        img_target = self._get_img(name)
        h, w = img_target.shape
        x, y = pos
        buffer = 3

        if base_area:
            bbox = [
                base_area[0] + x - w / 2 - buffer,
                base_area[1] + y - h / 2 - buffer,
                base_area[0] + x + w / 2 + buffer,
                base_area[1] + y + h / 2 + buffer
            ]
        else:
            bbox = None

        await asyncio.sleep(0.1)    # 都加点时间，看是否可以防止鼠标点击，游戏未响应

        # 不用_screenshot，以免改变self.screen_img
        img = ImageGrab.grab(bbox=bbox)
        img_np = np.array(img)
        img_bg = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)

        pos_list, max_val = self._find_img_pos(
            img_bg, img_target, threshold=threshold)
        if pos_list:
            return True
        else:
            self.logger.debug(
                f"_verify_monitor not pass: not found {name} near {pos}")
            return False

    async def monitor(self, names, area=None, timeout=10, threshold=0.8, verify=True, interval=0.5):
        """return (name, pos_list), or rease timeout_error"""
        if not isinstance(names, list):
            names = [names]

        async def _monitor():

            # 确保在timeout之前，至少有一次是full的eara
            # 缓存的位置不一定有
            # 多个name的情况下，缓存区域大小，不一定比每一个img的大小都大
            i = 0
            c = min(int(timeout / interval), 4)
            while True:
                i += 1
                if i % c != 0:
                    cache_area = self._cacher.get_cache_area(names, area)
                    temp_area = cache_area or area
                else:
                    temp_area = area

                if not self._area_check_ok(temp_area, names):
                    temp_area = area

                img_bg = self._screenshot(area=temp_area)

                for name in names:
                    img_target = self._get_img(name)
                    pos_list, max_val = self._find_img_pos(
                        img_bg, img_target, threshold=threshold)
                    if pos_list:
                        dx = temp_area[0] - area[0]
                        dy = temp_area[1] - area[1]
                        # 还原成实际的相对位置
                        pos_list = [(x + dx, y + dy) for (x, y) in pos_list]
                        self.logger.debug(
                            f"Found {name} at {pos_list}, max_val: {max_val}")
                        if verify:
                            res = await self._verify_monitor(name, pos_list[0], threshold, base_area=area)
                            if res:
                                return name, pos_list
                            else:
                                # 找到了，但位置不对，需要下一次截图
                                break
                        else:
                            return name, pos_list
                if temp_area == area:
                    # 全量匹配耗时较长，所以
                    i += 1
                    await asyncio.sleep(interval * 2)
                else:
                    await asyncio.sleep(interval)

        self.logger.debug(f'start monitor: {names}')

        try:
            name, pos_list = await asyncio.wait_for(_monitor(), timeout=timeout)
            found_area = self._calc_found_area(name, pos_list[0], area)
            self._cacher.update_cache_area(name, found_area, area)
            self._count += 1
            if self._count % 20 == 19:
                self._cacher.save_data()
            return name, pos_list
        except asyncio.TimeoutError:
            msg = (f"monitor {names} timeout. ({timeout} s)")
            self.logger.debug(msg)
            raise FindTimeout(msg)

    def _calc_found_area(self, name, pos, area, buffer=5):
        img_target = self._get_img(name)
        h, w = img_target.shape
        x, y = pos
        dx, dy, _, _ = area
        bbox = (
            int(dx + x - w / 2 - buffer),
            int(dy + y - h / 2 - buffer),
            int(dx + x + w / 2 + buffer),
            int(dy + y + h / 2 + buffer)
        )
        return bbox

    def _area_check_ok(self, temp_area, names):
        """确保template.size > img.size"""
        x0, y0, x1, y1 = temp_area
        w_t = x1 - x0
        h_t = y1 - y0

        for name in names:
            img_target = self._get_img(name)
            h, w = img_target.shape
            if w_t < w or h_t < h:
                self.logger.debug(f"template size: ({w_t}, {h_t})")
                self.logger.debug(f"{name} img size: ({w}, {h})")
                self.logger.warn("tmplate.size is small then img.size")
                return False

        return True

    def is_exist(self, name,  area=None, threshold=0.8):
        img_bg = self._screenshot(area=area)
        img_target = self._get_img(name)
        pos_list, max_val = self._find_img_pos(
            img_bg, img_target, threshold=threshold)
        if pos_list:
            self.logger.debug(
                f"{name} is exist at {pos_list}, max_val: {max_val}")
            return True
        return False

    def _screenshot(self, area=None, name=None):
        """grab the screen img"""
        # start_t = time.time()

        img = ImageGrab.grab(bbox=area)

        # Convert PIL.Image to bgr_img
        img_np = np.array(img)

        rgb_img = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        # self.screen_img = img
        self.screen_img = img_np

        if name:
            # 用cv2读取了一幅图片，读进去的是BGR格式的，
            # 但是在保存图片时，要保存为RGB格式的
            rgb_img.save(name)

        img_gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)

        # time_cost = time.time() - start_t
        # self.logger.debug(f"screenshot cost: {time_cost} s")

        return img_gray
        # return rgb_img

    def _get_img(self, name):
        """return img obj according to its name"""
        if name in self.img_dict:
            return self.img_dict[name]

        for root, dirs, files in os.walk(pic_dir):
            for f in files:
                f_name = os.path.splitext(f)[0]
                if f_name == name:
                    path = os.path.join(root, f)
                    img = self._read_pic(path)
                    self.img_dict[name] = img
                    return img
        else:
            msg = f"can't found the {name}, in {pic_dir}"
            raise Exception(msg)

    def _read_pic(self, pic_path):
        """read pic file, return img_gray object"""
        pic_path = os.path.abspath(pic_path)
        if not os.path.exists(pic_path):
            cwd_dir = os.getcwd()
            msg = f"{cwd_dir}: The {pic_path} isn't exists."
            raise Exception(msg)
        img = cv2.imread(pic_path, 0)
        return img

    def _find_img_pos(self, img_bg, img_target, threshold):
        """find the position of the target_image in background_image.

        return (postions, max_val, max_loc)
        """
        res = cv2.matchTemplate(img_bg, img_target, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        locs = np.where(res >= threshold)

        if len(locs[0]) == 0:
            return ([], 0)

        pos_list = list(zip(*locs[::-1]))
        pos_list.insert(0, max_loc)    # 使得默认能获取匹配度最高的位置
        pos_list = self._de_duplication(pos_list)
        pos_list = self._to_center_pos(pos_list, img_target)

        return (pos_list, max_val)

    def _de_duplication(self, pos_list, offset=10):
        """去掉匹配到的重复的图像坐标"""
        new_list = []

        for (x, y) in pos_list:
            if not new_list:
                new_list.append((x, y))
            else:
                for (x1, y1) in new_list[:]:
                    if x1 - offset < x < x1 + offset and \
                            y1 - offset < y < y1 + offset:
                        break
                else:
                    new_list.append((x, y))

        return new_list

    def _to_center_pos(self, pos_list, img_target):
        """转化为图像中心的坐标"""
        h, w = img_target.shape
        new_pos_list = []

        for i, pos in enumerate(pos_list):
            x = int(pos[0] + (w / 2))
            y = int(pos[1] + (h / 2))
            new_pos_list.append((x, y))

        return new_pos_list


async def test(names, bbox=None, threshold=0.8, max_try=1, verify=True):
    if isinstance(names, str):
        names = [names]

    eye = Eye()
    t1 = time.time()

    all_res = []

    for _ in range(max_try):
        res = await eye.find_all_pos(names, area=bbox, threshold=threshold, verify=verify)
        all_res.extend(res)

    all_res = eye._de_duplication(all_res)
    print(all_res)
    
    t2 = time.time()
    print("cost time: {:.2f}".format(t2 - t1))

    if len(all_res) > 1:
        # show match img
        img_rgb = ImageGrab.grab(bbox=bbox)
        img_rgb = np.array(img_rgb)
        img_target = eye._get_img(names[0])
        h, w = img_target.shape
        for pt in all_res:
            cv2.rectangle(img_rgb, (pt[0] - int(w/2), pt[1] - int(h/2)),
                        (pt[0] + int(w/2), pt[1] + int(h/2)), (0, 0, 255), 2)

        cv2.imwrite('res.png', img_rgb)
        img = Image.open('res.png')
        img.show()


