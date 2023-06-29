import asyncio

from lib.global_vals import *
from tasks.task import Task




class XingYunZhuanPan(Task):
    """幸运转盘"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._move_to_right_top()
        await self.player.find_then_click('lucky_draw')
        await self.player.find_then_click('draw_once')
        await asyncio.sleep(8)
        await self.player.find_then_click('draw_again')

        self._increate_count('count', 2)

    def test(self):
        if not self.cfg['XingYunZhuanPan']['enable']:
            return False
        if self._get_count('count') >= 2:
            return False
        return True
