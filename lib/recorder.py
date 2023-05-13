##############################################################################
# 记录每个角色的任务执行情况
# 默认按窗口区分，如果配置了游戏账户就按账户区分
#
##############################################################################

"""
{
    date: 2023-05-01,
    run_count: 1,

    YouJian: {
        receive_count: {
            "value": 10,
            "expired_date": "2023-05-02",
        },
    },

    "YiJiMoKu": {
        count: {
            "value": 10,
            "expired_date": "2023-05-05",
        },
    },
    ...
}
"""

import os
import json
from datetime import datetime, timedelta
from lib.mylogs import make_logger


class PlayCounter(object):
    def __init__(self, name):
        _dir = 'record'
        if not os.path.exists(_dir):
            os.mkdir(_dir)
        self._file = os.path.join(_dir, name + '.json')

        self.logger = make_logger('full')

        self.today = datetime.now()
        self.today_str = datetime.now().strftime(r'%Y-%m-%d')

        if name == 'debug':
            self._init_data()
        elif not os.path.exists(self._file):
            self._init_data()
        else:
            self._load_data()

    def _init_data(self):
        self.logger.debug('init recorder data')
        self._data = {}
        self._data['date'] = self.today_str
        self._data['run_count'] = 1

    def _load_data(self):
        try:
            with open(self._file, 'r') as f:
                self._data = json.load(f)
        except json.decoder.JSONDecodeError as err:
            self.logger.error(f'load {self._file} failed: {str(err)}')
            os.remove(self._file)
            return self._init_data()

    def get_run_count(self):
        return self._data['run_count']
    
    def get_global(self, key, default=0):
        return self._data[key]
    
    def set_global(self, key, val):
        self._data[key] = val

    def get(self, cls_name, key, default=0):
        try:
            expired_date = self._data[cls_name][key]['expired_date']
            if self.today_str < expired_date:
                return int(self._data[cls_name][key]['value'])
            else:
                return default
        except KeyError:
            return default

    def set(self, cls_name, key, val, validity_period=1):
        if cls_name not in self._data:
            self._data[cls_name] = {}

        if key not in self._data[cls_name]:
            self._data[cls_name][key] = {}

        d = self._data[cls_name][key]
        d['value'] = val
        d['expired_date'] = self._days_later(validity_period)

    def _days_later(self, num):
        date = self.today + timedelta(days=num)
        return date.strftime(r'%Y-%m-%d')

    def save_data(self):
        with open(self._file, 'w') as f:
            json.dump(self._data, f)
