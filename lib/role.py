from lib.read_cfg import read_role_cfg
import logging
from lib.player import Player, FindTimeout
from lib.windows import Window
import asyncio
import configparser


# TODO setting 先继承default，然后再载入自定义的
# 官方提供 小号、高氪金 的配置扩展

class Role(object):
    def __init__(self, game=None, user=None):
        self.game = game
        self.user = user

    def __eq__(self, other):
        return self.game == other.game and self.user == other.user

    def __str__(self):
        return f"Role ({self.game}, {self.user})"

    # [1]
    # game = mo_shi_jun_tun
    # user = aa592729440
    # passwd = aa
    # setting = default
    async def load_all_attributes(self):
        # load from account.cfg
        config = configparser.RawConfigParser()
        config.read(r'./configs/account.cfg', encoding='utf-8')

        for s in config.sections():
            game = config.get(s, 'game')
            user = config.get(s, 'user')
            if game == self.game and user == self.user:
                self.passwd = config.get(s, 'passwd')
                self.cfg_name = config.get(s, 'setting')
                break
        else:
            self.passwd = ''
            self.cfg_name = 'basic'

        # load from roles_setting and ext_roles_setting
        self.play_setting = {}
        config = configparser.RawConfigParser()
        config.read(
            f'./configs/roles_setting/{self.cfg_name}.cfg', encoding='utf-8')
        for sct in config.sections():
            if sct not in self.play_setting:
                self.play_setting[sct] = {}
            for opt in config[sct]:
                val = config.get(sct, opt).lower().strip()
                if val == 'yes':
                    val = True
                elif val == 'no':
                    val = False
                self.play_setting[sct][opt] = val
