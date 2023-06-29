import asyncio

from lib.global_vals import *
from tasks.task import Task



class MeiRiQianDao(Task):
    """每日签到"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('jing_cai_huo_dong')
        for _ in range(3):
            await self.player.find_then_click('qian_dao')

        self._increate_count('count', 1)

        # 领取周礼包、月礼包
        for pos in await self.player.find_all_pos('red_point2'):
            await self.player.click((pos[0] - 80, pos[1] + 30))
            await self.player.monitor('mian_fei')
            await self.player.click((405, 250))
            await self.player.find_then_click('5_xing_sui_pian')
            await self.player.find_then_click('ok_btn2')
            await self.player.find_then_click('mian_fei')
            await self.player.find_then_click(OK_BUTTONS)

    def test(self):
        return self.cfg['MeiRiQianDao']['enable']
