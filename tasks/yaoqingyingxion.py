import asyncio

from lib.global_vals import *
from tasks.task import Task




class YaoQingYingXion(Task):
    """邀请英雄"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_down()
        await self.player.find_then_click('invite_hero')
        await self.player.monitor('beer')
        pos_list = await self.player.find_all_pos(['invite_free', 'invite_soda', 'invite_beer'])

        for p in pos_list:
            if p[0] > 300:    # 是右边的高级邀请按钮
                self._increate_count('count_gao_ji_yao_qing')
            else:
                self._increate_count('count_pu_tong_yao_qing')

            await self.player.click(p)
            name, _ = await self.player.monitor(['ok9', 'ok10', 'ok17', 'close'])
            # 如果英雄列表满了，就遣散英雄
            if name == 'close':
                self.logger.warning(
                    "The hero list is full, so need dismiss heroes")
                pos_list.append(p)    # 没邀请成功，就再试一次
                await self.player.find_then_click('qian_san_btn')
                await self._dismiss_heroes()
            else:
                await self.player.find_then_click(name)    # 要避免点太快

        # 购买光暗3星
        if self._get_count('mai_guang_an_3_xing') > 0:
            return
        
        await self.player.find_then_click('pi_jiu_icon')
        await self.player.monitor('pi_jiu_icon1')
        await self._swipe_left()

        for _ in range(2):
            try:
                _, pos = await self.player.monitor(['guang_san_xing', 'an_san_xing'], threshold=0.9, timeout=2)
                await self.player.click((pos[0], pos[1] + 80))
                await self.player.find_then_click('max2')
            except FindTimeout:
                # 买完了，或者币不够了
                break
            
            await self.player.find_then_click('gou_mai')
            await self.player.find_then_click(OK_BUTTONS)
        
        self._increate_count('mai_guang_an_3_xing', validity_period=7)
        


    def test(self):
        if not self.cfg['YaoQingYingXion']['enable']:
            return False
        if self._get_count('count_gao_ji_yao_qing') >= 1:
            return False
        return True

    async def _dismiss_heroes(self):
        await self.player.find_then_click('1xing')
        await self.player.find_then_click('quick_put_in')
        await self.player.find_then_click('2xing')
        await self.player.find_then_click('quick_put_in')

        # 如果遣散栏为空，就遣散3星英雄
        try:
            await self.player.monitor('empty_dismiss', timeout=1)
        except FindTimeout:
            await self.player.find_then_click('dismiss')
            await self.player.find_then_click('receive1')
        else:
            await self.player.find_then_click('3xing')
            await self.player.find_then_click('quick_put_in')
            await self.player.find_then_click('dismiss')
            await self.player.find_then_click(OK_BUTTONS)
            await self.player.find_then_click('receive1')

        # 回到啤酒邀请界面
        await self.player.go_back()


    async def _swipe_left(self):
        p1 = (650, 275)
        p2 = (250, 275)
        await self.player.drag(p1, p2, stop=True)
