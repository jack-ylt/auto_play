import asyncio
from lib.helper import is_afternoon, is_monday, choose_pos
from lib.global_vals import *
from tasks.task import Task





class JingJiChang(Task):
    """竞技场"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()
        self.num = int(self._get_cfg('fight_num'))
        self.count = self._get_count('count')

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_top()
        await self.player.find_then_click('arena')
        await self.player.find_then_click('enter')

        if is_afternoon:
            c = self.count
            if is_monday() and self.num >= 7:
                num = self.num + 1 - c     # 确保一周战斗50次
            else:
                num = self.num - c
        else:
            num = min(3, self.num - self.count)

        win, lose = 0, 0
        page = 0
        for i in range(num):
            try:
                page = await self._choose_opponent(page)
            except PlayException:
                return

            if await self._fight_win():
                win += 1
            else:
                lose += 1
                page += 1

        self.logger.debug(
            f"JingJiChang: win: {win}, lose: {lose}, page: {page}")
        self._increate_count('count', num)

        await self._collect_award()

    def test(self):
        if not self.cfg['JingJiChang']['enable']:
            return False
        if self.count >= self.num:
            return False
        if (not is_afternoon()) and self.count >= 3:
            return False
        return True

    async def _choose_opponent(self, page=0):
        # 避免速度太快，把确定误识别战斗
        await self.player.monitor('fight_ico')
        await self.player.find_then_click('fight7')

        # 经常 monitor fight8 超时，所以多试一次
        await asyncio.sleep(2)
        await self.player.find_then_click('fight7', timeout=1, raise_exception=False)

        for _ in range(page):
            self.player.find_then_click('refresh5')

        for _ in range(2):
            await self.player.monitor('fight8')
            pos_list = await self.player.find_all_pos('fight8')
            await self.player.click(choose_pos(pos_list, 'bottom'))
            name, _ = await self.player.monitor(['buy_ticket', 'start_fight'])

            if name == 'start_fight':
                await self.player.click_untile_disappear('start_fight')
            else:
                raise PlayException('lack of ticket.')

            await asyncio.sleep(3)    # 避免速度太快
            try:
                # 同一个人不能打太多次
                # 结算前5分钟不能战斗
                # TODO 这种情况，不要_verify_monitor，就可以准确判断是那种情况了
                await self.player.monitor('close8', timeout=1)
            except FindTimeout:
                return page
            else:
                await self.player.find_then_click('close8')
                await self.player.find_then_click('refresh5')
                page += 1

        # 如果两次都无法进入战斗，可能是在结算期了
        raise PlayException('_choose_opponent failed')

    async def _fight_win(self):
        name_list = ['card', 'fast_forward1', 'go_last']
        while True:
            name, pos = await self.player.monitor(name_list, threshold=0.9, timeout=10)
            if name == 'card':
                await self.player.click_untile_disappear('card')
                await self.player.click(pos)
                break
            else:
                await self.player.click(pos)
            await asyncio.sleep(1)

        res, _ = await self.player.monitor(['win', 'lose'])
        await self.player.find_then_click(OK_BUTTONS)
        return res

    async def _collect_award(self):
        await self.player.find_then_click('award')
        await self.player.monitor('receive_list')
        while True:
            pos_list = await self.player.find_all_pos('receive2')
            if not pos_list:
                break
            await self.player.click(choose_pos(pos_list, 'top'))
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=2)
            except FindTimeout:
                break
