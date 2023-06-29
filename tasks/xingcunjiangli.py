import asyncio

from lib.global_vals import *
from tasks.task import Task




class XingCunJiangLi(Task):
    """幸存奖励

    一天领一次就可以了，以便于一次性完成所有日常任务
    """

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()

    async def run(self):
        if not self.test():
            return

        pos_plus = (412, 54)
        pos_receive = (350, 390)

        await self.player.click(pos_plus, cheat=False)
        await self.player.monitor('xing_cun_jiang_li')
        for _ in range(2 - self._get_count()):
            await self.player.click(pos_receive)
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=2)
                self._increate_count()
            except FindTimeout:
                break

    def test(self):
        return self._get_cfg('enable') and self._get_count() < 2
