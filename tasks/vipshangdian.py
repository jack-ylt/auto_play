import asyncio

from lib.global_vals import *
from tasks.task import Task




class VipShangDian(Task):
    """VIP商店"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        pos_vip = (28, 135)
        await self.player.click(pos_vip, cheat=False)
        await self.player.monitor(['vip_shop', 'vip_shop1'])
        try:
            await self.player.find_then_click('receive_small', timeout=1)
        except FindTimeout:
            pass
        self._increate_count('count')

    def test(self):
        return self.cfg['VipShangDian']['enable'] and self._get_count('count') < 1
