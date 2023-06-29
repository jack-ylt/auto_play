import asyncio

from lib.global_vals import *
from tasks.task import Task




class YongZheFuBen(Task):
    """勇者副本"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._enter()

        for i in range(15):
            try:
                await self._goto_fight()
            except FindTimeout:
                self.logger.debug('goto fight failed, check if finished.')
                if await self._finished():
                    return

            # 每一期, 第一次进入可能都要重新设置阵容
            if i == 0:
                await self._equip_team()
                try:
                    await self.player.monitor('lack_of_hero', timeout=1)
                    self.logger.debug('skip, lack 0f heroes.')
                    return
                except FindTimeout:
                    pass

            if not await self._fight_win():
                await self.player.find_then_click(OK_BUTTONS)
                return

    def test(self):
        return self.cfg['YongZheFuBen']['enable']

    async def _enter(self):
        await self._move_to_right_top()
        await self.player.find_then_click('brave_instance')
        await self.player.monitor('brave_coin')

    async def _goto_fight(self):
        # current_level: 第一次进入
        # ok：非第一次，非vip
        # next_level4：非第一次，vip
        name, pos = await self.player.monitor(['huo_de_wu_ping', 'next_level4', 'ok', 'current_level'], timeout=2, verify=False)
        if name == 'huo_de_wu_ping':
            await self.player.find_then_click(OK_BUTTONS)
            name, pos = await self.player.monitor(['next_level4', 'ok', 'current_level'], timeout=2, verify=False)

        if name == 'next_level4':
            await self.player.click(pos)
            await self.player.click_untile_disappear('challenge4')
            return True
        elif name == 'ok':
            await self.player.click(pos)
            await self.player.monitor('brave_coin')

        try:
            # 获得物品可能会这时候弹出来
            await self.player.monitor('huo_de_wu_ping', timeout=2)
            await self.player.find_then_click(OK_BUTTONS)
        except FindTimeout:
            pass

        _, (x, y) = await self.player.monitor('current_level', threshold=0.95, timeout=5)
        await self.player.click((x, y + 35), cheat=False)
        await self.player.click_untile_disappear('challenge4')

    async def _fight_win(self):
        # await self.player.find_then_click('start_fight')
        await self.player.click_untile_disappear('start_fight')

        # 5次不一定够用，因为不要60级，无法go_last
        # for _ in range(5):
        while True:
            # 10s 有时候会timeout
            name, pos = await self.player.monitor(['card', 'lose', 'win', 'go_last', 'fast_forward1', 'huo_de_wu_ping'], timeout=20)
            if name == "card":
                await self.player.click_untile_disappear('card')
                await self.player.click(pos)
                return True
            elif name == 'win':
                return True
            elif name == 'huo_de_wu_ping':
                await self.player.find_then_click(OK_BUTTONS)
            elif name in ['go_last', 'fast_forward1']:
                await self.player.click(pos)
            else:
                return False
            await asyncio.sleep(1)

    async def _finished(self):
        await self.player.monitor('brave_coin')
        try:
            await self.player.monitor('brave_finished', timeout=1)
            self.logger.debug('YongZheFuBen is finished.')
            return True
        except FindTimeout:
            return False

