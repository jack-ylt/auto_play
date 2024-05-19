import asyncio

from lib.global_vals import *
from tasks.task import Task



class JueDiQiuSheng(Task):
    """绝地求生"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('yue_du_huo_dong')
        await self.player.find_then_click('jue_di_qiu_sheng')

        y = 400
        for x in (390, 540, 690):
            for i in range(20):
                await self.player.monitor('hui_zhang2')

                # 战力高的，现在能打穿月度BOOS了
                idx = (390, 540, 690).index(x)
                if self.exist(f'yi_tong_guo_{idx}'):
                    break

                await self.player.click((x, y))    # click fight btn
                await self.player.monitor('sao_dang2', timeout=5)
                    
                # 1 票打不死，就停止
                if self.player.is_exist('bai_fen_bai', threshold=0.9):
                    await self.player.find_then_click('sao_dang2')
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.click_untile_disappear('start_fight')
                    await self.player.monitor('huo_de_wu_ping')
                    await self.player.find_then_click(OK_BUTTONS)
                else:
                    await self.player.find_then_click(CLOSE_BUTTONS)
                    break
        
        self._increate_count(validity_period=15)

    def test(self):
        return self._get_cfg('enable') and self._get_count() < 1
