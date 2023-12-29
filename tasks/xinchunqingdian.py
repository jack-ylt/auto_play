import asyncio

from lib.global_vals import *
from tasks.task import Task


class XinChunQingDian(Task):
    """新春庆典"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        if not self.exist('fu_icon'):
            # 活动结束了
            return
        
        await self.click('fu_icon')
        await self.find(['hong_bao_lock', 'hong_bao_ok'])
        if not self.exist('hong_bao'):
            # 玩家自己做了活动
            self._increate_count('count')
            return

        await self.click('hong_bao')
        await self.click(OK_BUTTONS)

        await self.click('deng_long', until_disappear=False)
        await self.click('dian_deng_qi_fu')
        await self.click(OK_BUTTONS)

        self._increate_count('count')

    def test(self):
        # return self._get_cfg('enable') and self._get_count('count') < 1
        return self._get_cfg('enable') and self._get_count() < 1
        return True
