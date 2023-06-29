import asyncio

from lib.global_vals import *
from tasks.task import Task



class MiGong(Task):
    """迷宫"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        self._increate_count('count')
        try:
            await self.player.find_then_click('maze4', timeout=2, cheat=False)
        except FindTimeout:
            self.logger.debug("There is no maze")
            return

        await self.player.monitor('maze_text')
        await self.player.find_then_click('maze_daily_gift')

        try:
            _, pos = await self.player.monitor('red_point1', timeout=1)
        except FindTimeout:
            self.logger.debug("maze daily gift have been already recived.")
            return

        await self.player.click((pos[0] - 60, pos[1] + 20))

    def test(self):
        return self.cfg['MiGong']['enable'] and self._get_count('count') < 1

