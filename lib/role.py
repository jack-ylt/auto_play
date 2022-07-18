from lib.read_cfg import read_role_cfg
import logging
from lib.player import Player, FindTimeout
from lib.windows import Window
import asyncio
import configparser
from lib.read_cfg import read_game_user
from lib.recorder import PlayCounter

# TODO setting 先继承default，然后再载入自定义的
# 官方提供 小号、高氪金 的配置扩展


class Role():
    """游戏角色
    
    用来管理游戏账号、秘密，角色配置
    """
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


class Roles():
    """用于管理所有role"""
    def __init__(self):
        self._running_roles = []
        self._done_roles = []
        self.all_roles = [Role(g, u) for (g, u) in read_game_user()]
        self.total_roles = len(self.all_roles)

        for role in self.all_roles:
            counter = PlayCounter(role.game + '_' + role.user)
            role._run_count = counter.get_run_count()

        self._idle_roles = sorted(self.all_roles, key=lambda x: x._run_count)

        if not self._idle_roles:
            raise Exception("Error: 游戏账号未配置！请先参考文档配置游戏账号。")

    def get_idle_role(self, game=None):
        idle_role = None

        for r in self._idle_roles:
            if game and r.game == game:
                idle_role = r
                break
            idle_role = r
            break
        
        if idle_role:
            self.set_role_status(idle_role, 'running')

        return idle_role

    def set_role_status(self, role, status):
        role_dict = {
            'idle': self._idle_roles,
            'running': self._running_roles,
            'done': self._done_roles
        }

        for stt in role_dict:
            if stt == status:
                role_dict[stt].append(role)
            else:
                try:
                    role_dict[stt].remove(role)
                except ValueError:
                    pass

    def is_all_roles_done(self):
        return len(self._done_roles) == self.total_roles
