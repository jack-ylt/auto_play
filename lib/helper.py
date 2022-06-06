
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
log_dir = os.path.join(main_dir, 'logs')

def get_window_region(window_name):
    x, y = WINDOW_DICT[window_name]
    w, h = WIDTH, HIGH
    return (x, y, x+w, y+h)


def de_duplication(pos_list, offset=10):
    """去掉匹配到的重复的图像坐标"""
    # new_list = []

    # for (x, y) in pos_list:
    #     if not new_list:
    #         new_list.append((x, y))
    #     else:
    #         for (x1, y1) in new_list[:]:
    #             if x1 - offset < x < x1 + offset and \
    #                     y1 - offset < y < y1 + offset:
    #                 break
    #         else:
    #             new_list.append((x, y))

    # return new_list

    new_list = []
    for (x, y) in pos_list:
        for (x1, y1) in new_list:
            if math.fabs(x - x1) < offset and math.fabs(y - y1) < offset:
                break
        else:
            new_list.append((x, y))
    return new_list

# 实现logger单例，避免多次make_logger, 导致日志重复打印
logger_dict = {}

def make_logger(name):
    if name in logger_dict:
        return logger_dict[name]

    today = datetime.now().strftime(r'%Y-%m-%d')
    # file_dir = os.path.join(log_dir, name)
    # if not os.path.exists(file_dir):
    #     os.mkdir(file_dir)
    file_name = os.path.join(log_dir, name + '_' + today + '.log')
    print(file_name)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # fh = handlers.RotatingFileHandler(filename, mode='a', maxBytes=5*1024*1024, backupCount=3)
    fh = handlers.TimedRotatingFileHandler(file_name, when='D', interval=1, backupCount=7)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s   %(levelname)s   %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger_dict[name] = logger
    return logger


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