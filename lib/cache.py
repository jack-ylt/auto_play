# 用于缓存查找到图片的区域，以提高查找效率

import json
import os
import shutil

from lib.helper import singleton
from lib.mylogs import make_logger
from lib.windows import Window

logger = make_logger('full')


@singleton
class Cacher():
    def __init__(self):
        _dir = 'cache'
        if not os.path.exists(_dir):
            os.mkdir(_dir)

        self._file = os.path.join(_dir, 'area_cache' + '.json')
        self._file_back = os.path.join(_dir, 'area_cache_default' + '.json') 
        if os.path.exists(self._file):
            self._data = self._load_data()
        else:
            self._data = {}

    def _load_data(self):
        try:
            with open(self._file, 'r') as f:
                data = json.load(f)
            return data
        except json.decoder.JSONDecodeError as e:
            logger.error(f'load {self._file} failed: {str(e)}. Use {self._file_back} instead')
            shutil.copy(self._file_back, self._file)
            with open(self._file_back) as f:
                data = json.load(f)
            return data

    def get_cache_area(self, names, base_area):
        a, b, c, d = 10000, 10000, 0, 0
        for key in names:
            if key in self._data:
                x0, y0, x1, y1 = self._data[key]
                dx, dy, _, _ = base_area    # 获得屏幕的实际区域，以便直接截图
                a = min(a, x0 + dx)
                b = min(b, y0 + dy)
                c = max(c, x1 + dx)
                d = max(d, y1 + dy)
            else:
                return None
        return (a, b, c, d)

    def update_cache_area(self, name, found_area, base_area):
        x0, y0, x1, y1 = found_area

        # 过滤无效的area
        if x0 < 0 or y0 < 0 or x1 > Window.WIDTH or y1 > Window.HIGH:
            logger.error(f"Skip update cache area, for invalid area: {found_area}")
            return

        dx, dy, _, _ = base_area
        # 计算从（0， 0）开始的相对区域
        x0, y0, x1, y1 = (x0 - dx, y0 - dy, x1 - dx, y1 - dy)

        key = str(name)
        if key in self._data:
            x2, y2, x3, y3 = self._data[key]
            # 取两个矩形的并集
            union_area = (min(x0, x2), min(y0, y2), max(x1, x3), max(y1, y3))
        else:
            union_area = (x0, y0, x1, y1)

        self._data[key] = union_area

    def save_data(self):
        with open(self._file, 'w') as f:
            json.dump(self._data, f)
