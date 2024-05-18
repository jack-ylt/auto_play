import asyncio

from lib.global_vals import *
from tasks.task import Task

GOOD_TASKS = [
            'task_3star',
            'task_4star',
            'task_5star',
            'task_6star',
            'task_7star'
        ]


class RenWuLan(Task):
    """任务栏"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

        self._tasks_to_finish = [
            'task_3star',
            'task_4star',
            'task_5star',
        ]

    async def run(self):
        if not self.test():
            return

        await self._enter()

        try:
            await self.player.monitor('receivable_task', timeout=1)
        except FindTimeout:
            self.logger.info("Skip, there is no receivable task")
            return

        try:
            await self._accept_all_tasks(GOOD_TASKS)
        except NoEnoughHero:
            pass

        await self._onekey_finish_tasks()

        try:
            await self._refresh_tasks()
            self._increate_count('refresh_num')
        except NoEnoughZuanShi:
            pass

        await self._accept_and_finish_left_tasks()

        self._increate_count('count')

    def test(self):
        # return self.cfg['RenWuLan']['enable'] and self._get_count('count') < 1
        return True

    async def _enter(self):
        try:
            await self.player.monitor('task_board', timeout=1)
        except FindTimeout:
            await self._move_to_center()
        await self.player.find_then_click('task_board')
        await self.player.monitor(['unlock', 'lock'])

    async def _accept_all_tasks(self, good_tasks='all'):
        for _ in range(5):
            await self._accept_tasks(good_tasks)
            await self._swip_to_right()

            try:
                await self.player.monitor('receivable_task', timeout=1, verify=False)
            except FindTimeout:
                return

            try:
                await self.player.monitor(['finish_btn', 'unlock_more'], timeout=1)
                break
            except FindTimeout:
                pass

            # 避免到主界面，还在死循环
            try:
                await self.player.monitor(['unlock', 'lock'], timeout=1)
            except FindTimeout:
                break

        # 到了右边，但可能还有receivable_task
        await self._accept_tasks(good_tasks)

    async def _accept_tasks(self, good_tasks='all'):
        list1 = await self.player.find_all_pos('receivable_task')
        if good_tasks != 'all':
            list2 = await self.player.find_all_pos(good_tasks, threshold=0.85)
            pos_list = self._merge_pos_list(list1, list2, dx=50)
        else:
            pos_list = list1

        for pos in pos_list:
            await self.player.monitor('receivable_task')
            await self.player.click(pos)
            await self.player.find_then_click('yi_jian_shang_zhen')
            await self.player.find_then_click('kai_shi_ren_wu')

            # 注意：有可能英雄不够，则需要关闭窗口，继续往下运行
            try:
                await self.player.find_then_click(CLOSE_BUTTONS, timeout=1)
                print("英雄不够")
                raise NoEnoughHero()
            except FindTimeout:
                pass
        return True

    async def _swip_to_right(self, stop=True):
        pos_r = (800, 300)
        pos_l = (10, 300)
        await self.player.drag(pos_r, pos_l, speed=0.02, stop=stop)

    async def _refresh_tasks(self):
        # if self._get_count('refresh_num') >= int(self._get_cfg('refresh_num')):
        #     return False
        await self.player.find_then_click('refresh4')
        await asyncio.sleep(2)
        try:
            await self.player.monitor('lack_of_diamond', timeout=1)
        except FindTimeout:
            
            return True
        else:
            await self.player.find_then_click(CLOSE_BUTTONS)
            raise NoEnoughZuanShi()

    async def _onekey_finish_tasks(self):
        # vip finish
        await self.player.find_then_click('one_click_collection2')
        try:
            await self.player.find_then_click(OK_BUTTONS, timeout=2)
            await asyncio.sleep(2)
            await self.player.find_then_click(OK_BUTTONS)
            self.logger.info("All tasks had been finished.")
            return
        except FindTimeout:
            pass

        # 非vip也只领取5星及以下的任务（保持一致性）
        for _ in range(5):
            list1 = await self.player.find_all_pos('finish_btn')
            list2 = await self.player.find_all_pos(self._tasks_to_finish)
            pos_list = self._merge_pos_list(list1, list2, dx=10)
            if pos_list:
                await self.player.click(sorted(pos_list)[0])
                await self.player.find_then_click(OK_BUTTONS)
                # 5星以上任务，会有两个ok确认
                await self.player.find_then_click(OK_BUTTONS, timeout=2, raise_exception=False)
            else:
                try:
                    await self.player.monitor('unlock_more', timeout=1)
                    break
                except FindTimeout:
                    await self._swip_to_right()

            # 避免到主界面，还在死循环
            try:
                await self.player.monitor(['unlock', 'lock'], timeout=1)
            except FindTimeout:
                break

    async def _accept_and_finish_left_tasks(self):
        """完成1星、2星任务

        以便一次性完成所有日常任务
        """
        for _ in range(10):
            try:
                await self.player.find_then_click('receivable_task', timeout=2)
                await self.player.find_then_click('yi_jian_shang_zhen')
                await self.player.find_then_click('kai_shi_ren_wu')
            except FindTimeout:
                break

            try:
                await self.player.find_then_click('diamond_0', timeout=2)
                await self.player.find_then_click(OK_BUTTONS)
            except FindTimeout:
                pass
