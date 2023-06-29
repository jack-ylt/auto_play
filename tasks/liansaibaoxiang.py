import asyncio

from lib.global_vals import *
from tasks.task import Task



class LianSaiBaoXiang(Task):
    """收集联赛宝箱"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        try:
            await self.player.find_then_click('lian_sai_bao_xiang', timeout=3)
        except FindTimeout:
            return

        await self.player.find_then_click('lian_sai_bao_xiang_l')
        await self.player.find_then_click(OK_BUTTONS)
        await self.player.go_back()
        self._increate_count()

    def test(self):
        return self._get_cfg('enable') and self._get_count('count') < 1
