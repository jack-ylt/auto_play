import asyncio
from datetime import datetime
from lib.global_vals import *
from tasks.task import Task



class ShiJieBoss(Task):
    """世界Boss"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        # 简单起见，小号不打这个世界Boos了
        try:
            # 可能是跨服联赛，没有boos可以打
            await self.player.find_then_click('shi_jie_boos')
            await self.player.find_then_click('gong_ji', timeout=3)
        except FindTimeout:
            return 
        await self.player.click_untile_disappear('start_fight')

        for i in range(10):
            await self.player.find_then_click('xia_yi_chang')
            await asyncio.sleep(3)

        await self.player.find_then_click(OK_BUTTONS)
        self._increate_count()

    def test(self):
        if self._get_cfg('enable') and datetime.now().weekday() in [0, 1] and self._get_count() < 1:
            return True
        return False

