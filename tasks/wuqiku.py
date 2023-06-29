import asyncio
import random
from lib.global_vals import *
from tasks.task import Task




class WuQiKu(Task):
    """武器库"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()

    async def run(self):
        if not self.test():
            return

        num_list = ['num_0', 'num_1', 'num_2', 'num_3']
        pos_quantity = (220, 330)
        pos_enter = (810, 480)
        pos_forging = (250, 450)

        await self._move_to_right_top()
        await self.player.find_then_click('armory')
        await self.player.monitor('armory_list')

        count = 0
        max_num = 3    # 每日任务要求锻造3次
        while True:
            pos = self._select_equipment_randomly()
            if not pos:
                break
            await self.player.click(pos)
            await self.player.information_input(pos_quantity, str(max_num - count))
            await self.player.click(pos_enter)
            name, _ = await self.player.monitor(num_list, threshold=0.9)
            count += num_list.index(name)
            await self.player.click(pos_forging)
            # 如果锻造数量是0的话，不会弹出对话框
            await self.player.find_then_click(OK_BUTTONS, timeout=3, raise_exception=False)

            if count >= 3:
                self._increate_count('count', 3)
                return

        self.logger.warning("There are not enough equipment for synthesis.")

    def test(self):
        return self.cfg['WuQiKu']['enable'] and self._get_count('count') < 3

    def _select_equipment_randomly(self):
        """随机选择锻造装备，不能每次都薅同一只羊"""
        pos_types = [
            (820, 190),
            (820, 270),
            (820, 350),
            (820, 440),
        ]

        while True:
            if len(self._seen) == len(pos_types):
                return ()
            pos = random.choice(pos_types)
            if pos not in self._seen:
                self._seen.add(pos)
                return pos
