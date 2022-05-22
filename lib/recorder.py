##############################################################################
# 记录每个角色的任务执行情况
# 默认按窗口区分，如果配置了游戏账户就按账户区分
#
##############################################################################

"""
{
    date: 2022-05-18,
    run_count: 1,
    YaoQingYingXion: {
        count: 0,
    }
    WuQiKu: {
        count: 0,
    }
    YouJian: {
        receive_count: 0,
    },
    HaoYou: {
        receive_count: 0,
        friend_boss: 0,
        my_boss: 2,
    },
    ...
}
"""

import os
import json
from datetime import datetime


TODAY = datetime.now().strftime(r'%Y-%m-%d')


class PlayCounter(object):
    def __init__(self, name):
        self._file = os.path.join('logs', name + '.json')
        if name == 'debug':
            self._init_data()
        else:
            self._load_data()

    def _load_data(self):
        if os.path.exists(self._file):
            with open(self._file, 'r') as f:
                self._data = json.load(f)
            if self._data['date'] == TODAY:
                self._data['run_count'] += 1
                return

        # 如果文件不存在，或者数据过期，重新初始化
        self._init_data()

    def _init_data(self):
        self._data = {}
        self._data['date'] = TODAY
        self._data['run_count'] = 1

    def get(self, cls_name, key):
        try:
            return self._data[cls_name][key]
        except KeyError:
            return 0

    def set(self, cls_name, key, val):
        if cls_name not in self._data:
            self._data[cls_name] = {}
        self._data[cls_name][key] = val

    def save_data(self):
        with open(self._file, 'w') as f:
            json.dump(self._data, f)
