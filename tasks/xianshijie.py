import asyncio

from lib.global_vals import *
from tasks.task import Task


class XianShiJie(Task):
    """现世界"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        """验证任务是否已经完成"""
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 3

    async def run(self):
        if not self.test():
            return

        await self._enter()

        await self._collect_box()
        if self._get_count('count') < 3:
            for _ in range(2):
                await asyncio.sleep(10)
                await self._collect_box()
            self._increate_count('count', 3)
        else:
            self._increate_count('count', 1)

        # 现在有自动推图功能了
        while True:
            try:
                await self._goto_next_fight()
            except PlayException:
                await self.player.click(self._back_btn)
                return

            res = await self._fight()
            if res == 'lose':
                await self.player.monitor('ranking_icon')
                await self.player.click(self._back_btn)
                return

    def test(self):
        return self.cfg['XianShiJie']['enable']

    async def _enter(self):
        try:
            await self.player.find_then_click('level_battle', timeout=1)
        except FindTimeout:
            await self._move_to_center()
            await self.player.find_then_click('level_battle')
        await self.player.monitor('ranking_icon')

        # 新号前10天，要领取奖励
        try:
            await self.player.monitor('song_hao_li', timeout=2)
        except FindTimeout:
            return
        else:
            name, pos = await self.player.monitor('ke_ling_qv')
            await self.player.click((pos[0], pos[1] - 50))
            await self.player.find_then_click(OK_BUTTONS)
            try:
                await self.player.find_then_click('close_btn1')
                await asyncio.sleep(1)
                await self.player.find_then_click('close_btn1', timeout=2)
            except FindTimeout:
                pass

    async def _collect_box(self):
        pos_box = (750, 470)
        await self.player.click(pos_box)
        await self.player.find_then_click('receive', raise_exception=False)

    async def _goto_next_fight(self):
        name, pos = await self.player.monitor(['upgraded', 'next_level', 'already_passed', 'fight'])
        if name == 'upgraded':
            await self._hand_upgraded()
            await self._goto_next_fight()
        elif name == 'next_level':
            await self._nextlevel_to_fight(pos)
        elif name == 'already_passed':
            # await self._passed_to_fight()
            raise PlayException("Skip, the user went back to level")
        else:    # fight
            await self.player.click_untile_disappear('fight')

    async def _hand_upgraded(self):
        try:
            await self.player.find_then_click('map_unlocked')
        except FindTimeout:
            return

        await asyncio.sleep(5)
        await self._enter()

    async def _nextlevel_to_fight(self, pos):
        """go from next_level to fight"""
        await self.player.click(pos)
        name, pos = await self.player.monitor(['search', 'fan_hui', 'level_low', 'reach_max_level'])
        if name == 'level_low' or name == 'reach_max_level':
            await self.player.click(pos)
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)
        elif name == 'search':
            await self.player.click(pos)
        else:
            _, pos = await self.player.monitor('fu_biao')
            if pos[0] > 700 and pos[1] < 150:
                # 前往下一个大关卡
                await self._goto_next_map()
            else:
                # 前往下一个小关卡
                await self._goto_next_area()

        await asyncio.sleep(3)
        await self.player.click_untile_disappear(['fight'])

    # TODO: 所有都完成了如何处理？
    async def _goto_next_map(self):
        self.logger.debug('goto next map')
        x_list = [200, 275, 355, 430, 510, 586, 660]
        y = 65
        for x in x_list:
            await self.player.click((x, y))
            await asyncio.sleep(2)
            pos_list = await self.player.find_all_pos(['point', 'point2', 'point3', 'point4'], threshold=0.88)
            # 正常是一个point都没有的，3个是作为buffer
            if len(pos_list) < 3:
                break

        # 每个大关卡的第一个区域坐标
        await self.player.click((200, 250))
        await self.player.find_then_click('ok1')

    async def _goto_next_area(self):
        await asyncio.sleep(5)
        self.logger.debug('goto next area')
        pos_list = await self.player.find_all_pos(['point', 'point2', 'point3', 'point4'], threshold=0.88)
        pos = await self._guess_next_pos(pos_list)
        await self.player.click(pos)
        await self.player.find_then_click('ok1')

    async def _guess_next_pos(self, pos_list):
        pos_list = sorted(pos_list)
        _, (x, y) = await self.player.monitor('fu_biao')

        # 只有最右下角的小地图，才需要往上点，去往下一个小地图
        if 600 < x < 700 and 300 < y < 420:
            new_list = pos_list[-7:]
            pos = sorted(new_list, key=lambda x: x[1])[0]
            return (pos[0], pos[1] - 50)
        else:
            pos = pos_1 = pos_list[-1]
            pos_2 = pos_list[-2]
            if pos_1[1] - pos_2[1] < -15:
                return (pos[0] + 50, pos[1] - 25)
            elif pos_1[1] - pos_2[1] > -15:
                return (pos[0] + 50, pos[1] + 25)
            else:
                return (pos[0] + 50, pos[1])

    async def _passed_to_fight(self):
        """go from already_passed to fight"""
        # TODO next_level2 可能误识别，这样点了就没反应
        await self.player.find_then_click(['next_level2', 'next_level3'], threshold=0.85)

        try:
            name, pos = await self.player.monitor(['search', 'level_low', 'reach_max_level'])
        except FindTimeout:
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)

        if name == 'level_low' or name == 'reach_max_level':
            await self.player.click(pos)
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)
        await self.player.click(pos)
        await asyncio.sleep(3)
        await self.player.click_untile_disappear(['fight'])
