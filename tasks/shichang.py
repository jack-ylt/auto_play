import asyncio

from lib.global_vals import *
from tasks.task import Task




class ShiChang(Task):
    """市场"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_down()
        await self.player.find_then_click('market')
        await self.player.monitor(['gold', 'diamond'])

        for _ in range(4):
            await self._buy_goods()
            if not await self._refresh_new_goods():
                break

        # 高级市场
        if self._get_count() < 1:
            self._increate_count()

            await self.player.find_then_click('gao_ji')
            try:
                await self.player.monitor('gold_30m')
            except FindTimeout:
                # 100级以上才解锁
                return

            if self._get_cfg('mai_lv_yao'):
                await self.player.find_then_click('gold_30m')
                try:
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                except FindTimeout:
                    # 如果金币不足，忽略
                    pass

            if self._get_cfg('mai_men_piao'):
                await self.player.find_then_click('xia_yi_ye')
                await self.player.find_then_click('gold_300k')
                try:
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                except FindTimeout:
                    # 如果金币不足，忽略
                    pass

            goods_list = []
            if self._get_cfg('mai_bao_tu'):
                goods_list.append('bao_tu')

            if self._get_cfg('mai_pi_jiu'):
                goods_list.append('pi_jiu1')

            if self._get_cfg('mai_hui_zhang'):
                goods_list.append('hui_zhang1')

            if goods_list:
                await self.player.find_then_click('xia_yi_ye', timeout=1, raise_exception=False)
                for goods in goods_list:
                    _, pos = await self.player.monitor(goods)
                    await self.player.click((pos[0], pos[1] + 70))
                    try:
                        await self.player.find_then_click(OK_BUTTONS)
                        await self.player.find_then_click(OK_BUTTONS)
                    except FindTimeout:
                        # 如果钻石不足，直接结束
                        self.logger.warning("钻石不足")
                        return

    def test(self):
        return self.cfg['ShiChang']['enable']

    async def _buy_goods(self):
        nice_goods = ['task_ticket', 'hero_badge', 'arena_tickets',
                      'soda_water', 'hero_blue', 'hero_green',
                      'hero_light_blue', 'hero_red', 'bao_shi',
                      'xing_pian_bao_xiang']
        list1 = await self.player.find_all_pos('gold')
        list2 = await self.player.find_all_pos(nice_goods)
        pos_list1 = self._merge_pos_list(list1, list2, dx=50, dy=(0, 100))

        list3 = await self.player.find_all_pos('diamond_1000')
        list4 = await self.player.find_all_pos('beer_8')
        pos_list2 = self._merge_pos_list(list3, list4, dx=50, dy=(0, 100))

        for pos in sorted(pos_list1 + pos_list2):
            if await self.player.is_disabled_button(pos):
                continue
            await self.player.click((pos[0] + 30, pos[1]))
            try:
                name, pos = await self.player.monitor(['lack_of_diamond', 'ok8'], timeout=3)
            except FindTimeout:
                # 金币不足，或者点击没反应
                continue
            else:
                if name == 'ok8':
                    # TODO 如果游戏反应太慢，这样可能会误判
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                else:
                    await self.player.find_then_click(CLOSE_BUTTONS)

    async def _refresh_new_goods(self):
        fresh_btn = (690, 135)
        await self.player.click(fresh_btn)
        try:
            await self.player.find_then_click('cancle', timeout=2)
            return False
        except FindTimeout:
            return True

