
from numpy import histogram
from lib.ui_data import HIGH, WIDTH, WINDOW_DICT
import math
import logging
import os
from logging import handlers
from datetime import datetime
import sys
import time
# from ui_data import HIGH, WIDTH, WINDOW_DICT
import win32api
import win32gui
from win32con import WM_INPUTLANGCHANGEREQUEST
import re
from lib.global_vals import *


# file_dir = os.path.split(os.path.realpath(__file__))[0]
# main_dir = os.path.split(file_dir)[0]
# 打成单文件，只有这个打包前后路径是一致的

mode = open('./configs/mode.txt').read().strip()
if mode == 'release':
    release = True
else:
    release = False

if release:
    main_dir = os.path.dirname(os.path.realpath(sys.executable))
    print("main_dir for release:", main_dir)
else:
    file_dir = os.path.split(os.path.realpath(__file__))[0]
    main_dir = os.path.split(file_dir)[0]
    print("main_dir for dev:", main_dir)

sys.path.insert(0, main_dir)


def get_window_region(window_name):
    x, y = WINDOW_DICT[window_name]
    w, h = WIDTH, HIGH
    return (x, y, x+w, y+h)


def de_duplication(pos_list, offset=10):
    """去掉匹配到的重复的图像坐标"""

    new_list = []
    for (x, y) in pos_list:
        for (x1, y1) in new_list:
            if math.fabs(x - x1) < offset and math.fabs(y - y1) < offset:
                break
        else:
            new_list.append((x, y))
    return new_list


def is_afternoon():
    t = time.localtime()
    hour = t.tm_hour
    return hour > 12


def is_monday():
    return datetime.now().weekday() == 0


def is_wednesday():
    return datetime.now().weekday() == 2


def is_sunday():
    return datetime.now().weekday() == 6


class GameNotResponding(Exception):
    pass


def change_language(lang="EN"):
    """
    切换语言
    :param lang: EN––English; ZH––Chinese
    :return: bool
    """
    LANG = {
        "ZH": 0x0804,
        "EN": 0x0409
    }
    hwnd = win32gui.GetForegroundWindow()
    language = LANG[lang]
    result = win32api.SendMessage(
        hwnd,
        WM_INPUTLANGCHANGEREQUEST,
        0,
        language
    )
    if not result:
        return True

def singleton(cls):
    """单例模式"""
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton

def format_text(text, format='str', line=0):
    lines = text.splitlines()
    # print(lines)

    res = lines[line]

    if format == 'str':
        match_list = re.findall(r'(\w+)', res)
    elif format == 'int':
        match_list = re.findall(r'(\d+)', res)
    else:
        raise TypeError(f"Unkown format {format}")
    
    res = sorted(match_list, key=lambda x: len(x))[-1]

    return res

def choose_pos(pos_list, choice):
    if choice == "first":
        return pos_list[0]
    elif choice == "rightmost":
        return max(pos_list)
    elif choice == "top":
        lst = sorted(pos_list, key=lambda x: x[1])
        return lst[0]
    elif choice == "bottom":
        lst = sorted(pos_list, key=lambda x: x[1])
        return lst[-1]
    else:
        raise InternalError(f"invalid args: {choice}")