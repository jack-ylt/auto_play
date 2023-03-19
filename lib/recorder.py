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
from datetime import datetime, timedelta
from lib.mylogs import make_logger

logger = make_logger('full')

TODAY = datetime.now().strftime(r'%Y-%m-%d')

def _days_later(num):
    date = datetime.now() + timedelta(days=num)
    return date.strftime(r'%Y-%m-%d')

SPECIAL_DICT = {
    'YiJiMoKu': {
        'expired_date': _days_later(4)
    },
    'JueDiQiuSheng': {
        'expired_date': _days_later(15)
    },
    'GuanJunShiLian': {
        'expired_date': _days_later(4)
    }
}


class PlayCounter(object):
    def __init__(self, name):
        _dir = 'record'
        if not os.path.exists(_dir):
            os.mkdir(_dir)
        self._file = os.path.join(_dir, name + '.json')

        if name == 'debug':
            self._init_data()
        elif not os.path.exists(self._file):
            self._init_data()
        else:
            self._load_data()

    def _load_data(self):
        try:
            with open(self._file, 'r') as f:
                self._data = json.load(f)
        except json.decoder.JSONDecodeError as e:
            logger.error(f'load {self._file} failed: {str(e)}')
            os.remove(self._file)
            return self._init_data()
        
        self._update_data()

    def _update_data(self):
        """重置过期数据"""
        if self._data['date'] == TODAY:
            self._data['run_count'] += 1
            return
        
        self._data['date'] = TODAY
        self._data['run_count'] = 1

        for k, v in self._data.items():
            if not isinstance(v, dict):
                continue

            if k in SPECIAL_DICT:
                expired_date = self._data[k].get('expired_date', TODAY)
                if expired_date <= TODAY:
                    self._data[k] = SPECIAL_DICT[k]
            else:
                self._data[k] = {}


    def _init_data(self):
        self._data = {}
        self._data['date'] = TODAY
        self._data['run_count'] = 1

        self._data.update(SPECIAL_DICT)
    

    
    def get(self, cls_name, key):
        try:
            return int(self._data[cls_name][key])
        except KeyError:
            return 0

    def get_run_count(self):
        return self._data['run_count']

    def set(self, cls_name, key, val):
        if cls_name not in self._data:
            self._data[cls_name] = SPECIAL_DICT.get(cls_name, {})
        self._data[cls_name][key] = val

    def save_data(self):
        with open(self._file, 'w') as f:
            json.dump(self._data, f)
