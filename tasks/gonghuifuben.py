##############################################################################
# 特殊类，专门用于给小号领取工会boos的箱子
# 用测试模式调用一次就好了
#
##############################################################################

import asyncio

from lib.global_vals import *
from tasks.task import Task



class GongHuiFuBen(Task):
    """公会副本批量开宝箱"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('gong_hui')
        name, _ = await self.player.monitor(['gong_hui_ling_di', 'join_guild'])
        if name == 'join_guild':
            return    # 还没有参加公会，则跳过

        await self.player.find_then_click('gong_hui_ling_di')
        await self.player.find_then_click('gong_hui_fu_ben')

        while True:
            await self.player.monitor('gong_hui_boos')
            if self.player.is_exist('gong_hui_box'):
                await self._collect_box()
            else:
                if self.player.is_exist('1-1', threshold=0.9):
                    break
                await self.player.find_then_click('left_btn')

    def test(self):
        return True

    async def _collect_box(self):
        await self.player.find_then_click('gong_hui_box')
        # await self.player.find_then_click('jiang_li')
        await self.player.monitor('gong_hui_boos_jiang_li')

        for i in range(4):
            if self.player.is_exist('gong_hui_card'):
                await self.player.find_then_click('gong_hui_card')
                break
            else:
                await self.player.find_then_click('right_btn')

        await self.player.find_then_click(CLOSE_BUTTONS)
        # await self.player.go_back()
