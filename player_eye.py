# -*-coding:utf-8-*-

##############################################################################
# 主要用于监控游戏状态，以及文字识别
# 给定一些图片（可以附加区域信息），能判断当前画面中含有哪个图片，以及位置在哪
# 给定一个区域，能识别该区域中的文字信息
#
##############################################################################


import cv2
import re
import numpy as np
from PIL import ImageGrab, Image
import time
# from aip import AipOcr
from datetime import date
import os
import asyncio
from helper import get_window_region
from text_recognition import find_text_pos

from ui_data import PIC_DICT, SCREEN_DICT
# from configs.config import config

# TODAY = str(date.today())
# LOG_FILE = 'log_' + TODAY + '.log'

import logging
logger = logging.getLogger(__name__)


class FindTimeout(Exception):
    """
    when no found and timeout, raise 
    """
    pass


# client = AipOcr(**config)
# options = {
#     'probability': 'true',
#     'detect_language': 'true'}

# {name: pic_path, ...}


def de_duplication(pos_list, offset=10):
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


class Eye(object):
    idx = 0

    def __init__(self):
        self.img_dict = {}    # {name: img_obj, ...}
        self.bg_dict = {}
        self._load_target_imgs()

    def _load_target_imgs(self):
        for name, path in PIC_DICT.items():
            img = self.read_pic(path)
            self.img_dict[name] = img

    def screenshot(self, back_name=None):
        """screenshot, and save as file.

        save full, left_top, left_down, right_top
        return the screen pic file path
        """
        im = ImageGrab.grab()
        im.save(SCREEN_DICT['screen'])

        # 另存一份，以免覆盖
        back_name = './pics/screen_' + str((self.idx + 1) % 2) + '.jpg'
        self.idx += 1
        im.save(back_name)

        img_rgb = cv2.imread(SCREEN_DICT['screen'])
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        self.bg_dict['full'] = img_gray

        for name in ['left_top', 'left_down', 'right_top']:
            new_im = im.crop(get_window_region(name))
            new_path = SCREEN_DICT['screen_' + name]
            new_im.save(new_path)
            img_rgb = cv2.imread(new_path)
            img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
            self.bg_dict[name] = img_gray

        return back_name

        # return self.bg_dict['full'], self.bg_dict['left_top'], self.bg_dict['left_down'], self.bg_dict['right_top']

    def read_pic(self, pic_path):
        """read pic file, return img_gray object"""
        if not os.path.exists(pic_path):
            msg = f"The {pic_path} isn't exists."
            raise Exception(msg)
        img = cv2.imread(pic_path, 0)
        return img

    def to_center_pos(self, pos_list, img_target):
        """转化为图像中心的坐标"""
        h, w = img_target.shape

        for i, pos in enumerate(pos_list):
            x = int(pos[0] + (w / 2))
            y = int(pos[1] + (h / 2))
            pos_list[i] = (x, y)

        return pos_list

    def find_img_pos(self, img_bg, img_target, threshold=0.9, debug=False):
        """find the position of the target_image in background_image.

        return a list of postions
        """
        res = cv2.matchTemplate(img_bg, img_target, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        locs = np.where(res >= threshold)
        if debug:
            msg = 'max_val:', max_val, 'max_loc', max_loc
            print(msg)

        if len(locs[0]) == 0:
            return []

        pos_list = list(zip(*locs[::-1]))
        pos_list.insert(0, max_loc)    # 使得默认能获取匹配度最高的位置
        pos_list = de_duplication(pos_list)
        pos_list = self.to_center_pos(pos_list, img_target)
        # logger.debug(f"pos_list: {pos_list}")

        if debug:
            print('len:', len(pos_list), 'pos_list:', pos_list)

        return pos_list

        # done 返回 去重后的 中心坐标 pos_list 就好，过滤交给业务去做
    def cut_image(self, image, x, y, w, h):
        """cut image file according to (left top width hight)"""
        region = image.crop((x, y, x+w, y+h))
        return region

    def find_text_pos(self, text, window_name=None):
        pic_path = self.screenshot()
        if window_name:
            pic_path = SCREEN_DICT['screen_' + window_name]

        # image_cuted = self.cut_image(image, *area)
        pos = find_text_pos(pic_path, text)
        return pos


def test(pic_path_list, similarity=0.96, quantity=1, total=3):
    """寻找合适的目标截图与匹配度

    使得成功匹配率在90%以上，且不会误匹配
    有些标志物会动，可能需要多个图片来综合匹配
    """
    sucess = 0
    miss = 0
    error = 0
    eye = Eye()
    img_targets = []
    for pic_path in pic_path_list:
        img_target = eye.read_pic(pic_path)
        img_targets.append(img_target)

    all_pos = []
    for i in range(total):
        print(i)
        # img_bg =
        eye.screenshot()
        img_bg = eye.bg_dict['full']

        for img_target in img_targets:
            pos_list = eye.find_img_pos(
                img_bg, img_target, threshold=similarity, debug=True)
            all_pos.extend(pos_list)

        all_pos = de_duplication(all_pos)
        print('all_pos:', all_pos)

        num_found = len(all_pos)
        print('num_found:', num_found)

        if num_found == quantity:
            sucess += 1
        elif num_found > quantity:
            # 可以偶尔匹配不上，但不能错匹配
            error += 1
        else:
            miss += 1
        # sleep(0.1)

    print(f"total: {total}, sucess: {sucess}, miss: {miss}, error: {error}")
    if error == 0 and (sucess / total > 0.9):
        print("Test result: pass")
    else:
        print("Test result: failed")


eye = Eye()


def monitor(names, timeout=5, speed=1, threshold=0.8, filter_func=None):
    """return (name, pos), or rease timeout_error"""
    def _monitor():
        eye.screenshot()
        img_bg = eye.bg_dict['full']

        for name in names:
            img_target = eye.img_dict[name]
            pos_list = eye.find_img_pos(
                img_bg, img_target, threshold=threshold)
            if pos_list:
                if filter_func:
                    pos = filter_func[pos_list]
                else:
                    pos = pos_list[0]
                print(name, pos)
                return name, pos

        return None

    logger.debug(f'start monitor: {names}')
    start = time.time()

    while time.time() - start < timeout:
        res = _monitor()
        if res:
            return res
        else:
            time.sleep(speed)

    msg = (f"monitor {names} timeout. ({timeout} s)")
    raise FindTimeout(msg)


def find(args_list):
    img_bg, img, threshold = args_list
    return eye.find_img_pos(img_bg, img, threshold)


async def dispatch(exe, g_queue, g_event, g_found):
    logger.debug('dispatch start ...')
    while True:
        await asyncio.sleep(0.6)
        item_list = []

        while not g_queue.empty():
            item = await g_queue.get()
            item_list.append(item)

        if not item_list:
            continue

        for k in ['left_top', 'left_down', 'right_top']:
            g_found[k] = []

        eye.screenshot()

        to_be_find = []
        name_list = []
        for item in item_list:
            window_name, pic_name_list, threshold = item
            img_bg = eye.bg_dict[window_name]
            for pic_name in pic_name_list:
                name_list.append((window_name, pic_name))
                img = eye.img_dict[pic_name]
                to_be_find.append([img_bg, img, threshold])

        idx = 0
        pre_name = None
        for pos_list in exe.map(find, to_be_find):
            window_name, pic_name = name_list[idx]
            # if pos_list:
            #     logger.debug(f"{window_name} found {pic_name} at {pos_list}")

            if pre_name is None:
                pre_name = window_name
            if window_name != pre_name:
                g_event.set()    # 某个客户端的所有查找任务都完成了，发通知
                pre_name = window_name
                g_event.clear()

            g_found[window_name].append((pic_name, pos_list))

            idx += 1

        g_event.set()    # 最后一个客户端的所有查找任务都完成了，发通知
        g_event.clear()


if __name__ == '__main__':
    pic_paths = [
        # PIC_DICT['next_level2'],
        PIC_DICT['level_60']
    ]
    similarity = 0.9
    quantity = 1
    test(pic_paths, similarity=similarity, quantity=quantity)

    # monitor(['emulator_icon'])
    
    # eye = Eye()
    # time.sleep(3)
    # print(eye.find_text_pos('S16'))
