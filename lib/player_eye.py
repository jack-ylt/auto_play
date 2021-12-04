# -*-coding:utf-8-*-

##############################################################################
# 主要用于监控游戏屏幕，以及文字识别
#
##############################################################################

import sys
import cv2
import re
import numpy as np
from PIL import ImageGrab, Image
import time
from datetime import date
import os
import asyncio
# from lib.helper import get_window_region
from lib.helper import get_window_region
from lib.ui_data import SCREEN_DICT
from copy import deepcopy


import logging


logger = logging.getLogger(__name__)

# 不加入系统路径，此文件单独运行，会报错：
# ModuleNotFoundError: No module named 'lib.text_recognition'
file_dir = os.path.split(os.path.realpath(__file__))[0]
main_dir = os.path.split(file_dir)[0]
sys.path.insert(0, main_dir)
pic_dir = os.path.join(main_dir, 'pics')


class FindTimeout(Exception):
    """
    when no found and timeout, raise
    """
    pass


class Eye(object):
    def __init__(self):
        self.img_dict = {}    # {name: img_obj, ...}
        self.screen_img = None

    # def get_lates_screen(self):
    #     return self.screen_img

    def get_lates_screen(self, area=None):
        img = ImageGrab.grab(bbox=area)
        img_np = np.array(img)
        return img_np

    def save_picture_log(self, msg="", ext=".jpg"):
        img = self.get_lates_screen()
        now = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
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

    async def find_all_pos(self, names, area=None, threshold=0.8):
        """return list of pos"""
        logger.debug(
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
                logger.debug(
                    f"Found {name} at {pos_list}, max_val: {max_val}")
                all_pos.extend(pos_list)

        all_pos = sorted(self._de_duplication(all_pos))

        if not all_pos:
            logger.debug(f'No find any pos of {names}')

        return all_pos

    async def monitor(self, names, area=None, timeout=10, threshold=0.8):
        """return (name, pos_list), or rease timeout_error"""
        async def _monitor():
            while True:
                img_bg = self._screenshot(area=area)
                for name in names:
                    img_target = self._get_img(name)
                    pos_list, max_val = self._find_img_pos(
                        img_bg, img_target, threshold=threshold)
                    if pos_list:
                        logger.debug(
                            f"Found {name} at {pos_list}, max_val: {max_val}")
                        return name, pos_list
                await asyncio.sleep(1)

        logger.debug(f'start monitor: {names}')

        try:
            name, pos_list = await asyncio.wait_for(_monitor(), timeout=timeout)
            return name, pos_list
        except asyncio.TimeoutError:
            msg = (f"monitor {names} timeout. ({timeout} s)")
            raise FindTimeout(msg)

    def _screenshot(self, area=None, name=None):
        """grab the screen img"""
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
        return img_gray

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
            msg = f"can't found {name}"
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


async def test(names, bbox=None):
    eye = Eye()
    t1 = time.time()

    res = await eye.find_all_pos(names, area=bbox)
    print(res)

    t2 = time.time()

    # eye.save_picture_log("hwllo world")

    print("cost time: {:.2f}".format(t2 - t1))



