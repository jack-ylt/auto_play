import asyncio

from lib.global_vals import *
from tasks.task import Task



class JiYiDangAnGuan(Task):
    """记忆档案馆"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._move_to_right_top()
        await self.player.find_then_click('ji_yi_dang_an_guan')
        await self.player.monitor('wen_hao')

        try:
            await self.player.find_then_click('yi_jian_ling_qv1', timeout=2)
            await self.player.find_then_click('receive4')
        except FindTimeout:
            pass
        else:
            self._increate_count()

    def test(self):
        return self._get_cfg('enable')
