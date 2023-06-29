import asyncio

from lib.global_vals import *
from tasks.task import Task
from lib.helper import choose_pos


class TiaoZhanFuben(Task):
    """挑战副本"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 6

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('tiao_zhan_fu_ben')
        await self.player.monitor(CLOSE_BUTTONS)

        for (x, y) in await self.player.find_all_pos('red_point'):
            await self.player.click((x-50, y+20))

            button_name = await self._click_bottom_button()
            if button_name == 'sao_dang':
                await self._sao_dang()
            else:
                await self._tiao_zhan()

            await self.player.find_then_click(CLOSE_BUTTONS)

        await self.player.find_then_click(CLOSE_BUTTONS)

    def test(self):
        return self.cfg['TiaoZhanFuben']['enable'] and self._get_count('count') < 6

    async def _click_bottom_button(self):
        await self.player.monitor(['mop_up', 'mop_up1', 'mop_up2', 'challenge3'])
        await asyncio.sleep(1)    # 等待页面稳定
        sao_dang_list = await self.player.find_all_pos(['mop_up', 'mop_up1', 'mop_up2'])
        tiao_zhan_list = await self.player.find_all_pos('challenge3')
        pos = choose_pos(tiao_zhan_list + sao_dang_list, 'bottom')

        await self.player.click(pos)

        if pos in sao_dang_list:
            return 'sao_dang'
        return 'tiao_zhan'

    async def _sao_dang(self):
        self._increate_count('count')
        # 有可能本来就只有一场扫荡
        name = await self.player.find_then_click(['next_game1'] + OK_BUTTONS)
        if name == 'next_game1':
            await self.player.find_then_click(OK_BUTTONS)
            self._increate_count('count')

    async def _tiao_zhan(self):
        await self.player.click_untile_disappear('start_fight')
        res = await self._fight_challenge()

        if res == 'win':
            self._increate_count('count')
            name = await self.player.find_then_click(['xia_yi_chang'] + OK_BUTTONS)
            if name == 'xia_yi_chang':
                await self._fight_challenge()
                self._increate_count('count')
        else:
            self.logger.warning("Fight lose in TiaoZhanFuben")

        await self.player.find_then_click(OK_BUTTONS)

    async def _fight_challenge(self):
        for _ in range(24):
            await self.player.find_then_click('go_last')
            try:
                await self.player.monitor('fight_report')
            except FindTimeout:
                continue
            else:
                break
        res, _ = await self.player.monitor(['win', 'lose'])
        return res
