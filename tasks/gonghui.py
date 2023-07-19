import asyncio

from lib.global_vals import *
from tasks.task import Task



class GongHui(Task):
    """公会"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('gong_hui')
        name, _ = await self.player.monitor(['gong_hui_ling_di', 'join_guild'])
        if name == 'join_guild':
            return    # 还没有参加公会，则跳过

        await self._gong_hui_qian_dao()

        # name, pos = await self.player.monitor(['tui_jian_gong_hui', 'gong_hui_ling_di'])
        # if name == 'tui_jian_gong_hui':
        #     return

        await self.player.find_then_click('gong_hui_ling_di')

        await self._gong_hui_gong_chang()

        if self._get_cfg('fight_boss') and self._get_count('fight_boss') < 1:
            await self.player.go_back_to('guild_factory')
            await self._gong_hui_fu_ben()
            self._increate_count('fight_boss')

        self._increate_count('count')

    def test(self):
        return self.cfg['GongHui']['enable']

    async def _gong_hui_qian_dao(self):
        await self.player.monitor('gong_hui_ling_di')
        await self.player.find_then_click('sign_in', threshold=0.95, timeout=1, raise_exception=False)

    async def _gong_hui_fu_ben(self):
        await self.player.find_then_click('gong_hui_fu_ben')
        await self.player.monitor('gong_hui_boos')

        name, pos = await self.player.monitor(['boss_card_up', 'boss_card_down'], threshold=0.92, timeout=3)
        # 匹配的是卡片边缘，而需要点击的是中间位置
        if name == 'boss_card_up':
            pos = (pos[0], pos[1]+50)
        else:
            pos = (pos[0], pos[1]-50)
        await self.player.click(pos)

        await self.player.monitor('ranking_icon2')
        await asyncio.sleep(1)
        if self.player.is_exist(['zuan_shi', 'zuan_shi1']):
            # 避免花费钻石
            return

        try:
            await self.player.find_then_click('fight4', threshold=0.8, timeout=2)
        except FindTimeout:
            return

        await self.player.monitor('start_fight')    # 确保界面刷出来
        if self.player.is_exist(['empty_box', 'empty_box5']):
            await self._equip_team()

        await self._fight_guild()

    async def _equip_team(self):
        await self.player.monitor('start_fight')    # 确保界面刷出来
        await asyncio.sleep(2)
        try:
            await self.player.monitor(['empty_box', 'empty_box5'], timeout=1)
        except FindTimeout:
            return

        pos_list = [(x, 230) for x in (190, 255, 365, 435, 500, 570)]
        await self.player.multi_click(pos_list)

        pos_list = [(x, 450) for x in (120, 185, 250, 320, 380, 450)]
        await self.player.multi_click(pos_list)

    async def _fight_guild(self):
        # next_fight = (520, 425)

        await self.player.click_untile_disappear('start_fight')
        await asyncio.sleep(5)
        await self._go_last()

        # await self.player.click(next_fight)
        await self.player.click_untile_disappear('next_fight')
        await self._go_last()

        await self.player.find_then_click('ok')
        await self.player.monitor('ranking_icon2', timeout=15)

    async def _go_last(self):
        # go_last 按钮有时候会被boos挡住，所以没用find_then_click
        await self.player.monitor(['message', 'go_last'])
        await asyncio.sleep(2)

        pos_go_last = (835, 56)
        for i in range(3):
            await self.player.click(pos_go_last, cheat=False)
            try:
                await self.player.monitor('fight_report', timeout=2)
                return
            except FindTimeout:
                self.logger.warning(f"try {i}, go_last failed.")
                pass

    async def _gong_hui_gong_chang(self):
        await self.player.find_then_click('guild_factory')

        try:
            for _ in range(2):
                await self.player.find_then_click(['order_completed', 'ok1'], timeout=3)
        except FindTimeout:
            pass

        await self.player.find_then_click('get_order')
        try:
            await self.player.monitor('start_order', timeout=1)
        except FindTimeout:
            pass
        else:
            await self.player.find_then_click('yi_jian_kai_shi_ding_dan')

        await self.player.find_then_click('donate_home')
        await self.player.find_then_click(self.cfg['GongHui']['donate'])
        try:
            await self.player.find_then_click(['ok5'], timeout=2)
        except FindTimeout:
            pass
