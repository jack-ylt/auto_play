import asyncio

from lib.global_vals import *
from tasks.task import Task



class JueDiKongJian(Task):
    """绝地空间"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self.camp_dict = {
            'xie_e': 0,
            'shou_hu': 1,
            'hun_dun': 2,
            'zhi_xu': 3,
            'chuang_zao': 4,
            'hui_mie': 5,
        }

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_top()
        await self.player.find_then_click('jedi_space')

        # 要80即才解锁
        try:
            await self.player.monitor('challenge5')
        except FindTimeout:
            self._increate_count()    # 用于verify, 表示完成了
            return

        await self._choose_camp()
        await self.player.find_then_click('challenge5')

        await self.player.monitor('ying_xiong_lie_biao')
        try:
            # 一关都没通过，就没有扫荡
            await self.player.find_then_click('mop_up3', timeout=2)
            # 扫荡完了，就不会弹出扫荡窗口
            await self.player.find_then_click(['max'], timeout=3, cheat=False)
            self._increate_count()
        except FindTimeout:
            return

        await self.player.find_then_click(OK_BUTTONS)

    def test(self):
        return self._get_cfg('enable') and self._get_count('count') < 1

    async def _choose_camp(self):
        left = (90, 240)
        right = (780, 240)

        num = self.camp_dict[self.cfg['JueDiKongJian']['camp']]

        if num == 0:
            return
        elif num <= 3:
            pos_button = left
        else:
            pos_button = right
            num = 6 - num

        for _ in range(num):
            await self.player.click(pos_button, cheat=False)
            await asyncio.sleep(0.5)
