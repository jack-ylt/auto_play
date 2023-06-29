import asyncio

from lib.global_vals import *
from tasks.task import Task



class GaoTaShiLian(Task):
    """高塔试炼"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        if not await self._enter():
            return False

        await self._do_fight()
        
        if self._get_count('fight_count') >= 50:
            self._shi_lian_bao_zang()
            await self.player.go_back_to('gao_ta_te_quan')
            self._shi_lian_shang_dian()
        
        self._increate_count()
        
    def test(self):
        return self._get_cfg('enable') and self._get_count() < 2 and self._get_count('fight_count') <= 30

    async def _enter(self):
        await self._move_to_right_top()
        await self.player.find_then_click('yong_shi_zhi_ta')
        await self.player.find_then_click('gao_ta_shi_lian')
        try:
            await self.player.monitor('gao_ta_te_quan')
            return True
        except FindTimeout:
            return False

    async def _do_fight(self):  
        for _ in range(10):
            await self.player.find_then_click(CLOSE_BUTTONS, raise_exception=False, timeout=3)
            await self.player.find_then_click('0_9', raise_exception=False, timeout=3)
            
            for _ in range(3):
                await self.player.find_then_click('tiao_zhan2')
                try:
                    await self.player.monitor('start_fight', timeout=3)
                except FindTimeout:
                    # 没票了
                    return

                await self._re_equip_team()

                await self.player.find_then_click('start_fight')
                res, _ = await self.player.monitor(['win', 'lose'])
                await self.player.find_then_click(OK_BUTTONS)
                self._increate_count('fight_count', validity_period=10)
                if res != "win":
                    break
    
    async def _re_equip_team(self):
        x_list = [180, 250, 370, 430, 500, 570]
        y = 230
        pos_list = [(x_list[c], y) for c in range(6)]

        await self.player.multi_click(pos_list)
        await self.player.find_then_click('yi_jian_shang_zhen1')
        
    async def _shi_lian_bao_zang(self):
        await self.player.find_then_click('gao_ta_te_quan')
        await self.player.monitor('bao_zang')
        await asyncio.sleep(1)
        await self.player.click((560, 310))
        
    async def _shi_lian_shang_dian(self):
        await self.player.find_then_click('shi_lian_hei_jin')
        await self.player.find_then_click('450')
        await self.player.find_then_click('max3')
        await self.player.find_then_click('gou_mai')
        await self.player.find_then_click(OK_BUTTONS)

       