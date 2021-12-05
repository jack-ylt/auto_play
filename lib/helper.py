
from numpy import histogram
from lib.ui_data import HIGH, WIDTH, WINDOW_DICT
import math
# from ui_data import HIGH, WIDTH, WINDOW_DICT

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
