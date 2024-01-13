import asyncio

from lib.global_vals import *
from tasks.renwulan import RenWuLan



# class RenWuLan300(RenWuLan):
#     def __init__(self, player, role_setting, counter):
#         super().__init__(player, role_setting, counter)
#         self._good_tasks = [
#             'zuan_shi_4xing',
#             'pi_jiu_4xing',
#             'task_5star',
#             'task_6star',
#             'task_7star'
#         ]
    
#     async def run(self):
#         await self._enter()
#         await asyncio.sleep(3)
#         await self._accept_all_tasks()

#         if not await self._refresh_tasks():
#             return

#         end = False
#         total_cost = 0
#         max_num = 4
#         while not end:
#             task_num = len(await self.player.find_all_pos('receivable_task'))

#             if task_num >= 3:
#                 # refresh tasks
#                 if not await self._refresh_tasks():
#                     end = True
#             else:
#                 # add tasks
#                 add_num = max_num - task_num
#                 total_cost += add_num
#                 await self._add_task(add_num)

#             if self.player.is_exist('task_7star'):
#                 print("刷到了7星任务")
#                 end = True

#             if not self.player.is_exist('receivable_task'):
#                 print("没有白信封了")
#                 end = True

#             # accept tasks
#             if not await self._accept_tasks():
#                 end = True
        
#         print(f"总共消耗白信封：{total_cost}")

#     async def _add_task(self, num):
#         for _ in range(num):
#             await self.player.click((290, 475))
#         await asyncio.sleep(3)

#     async def _refresh_tasks(self):
#         await self.player.find_then_click('refresh4')
#         await asyncio.sleep(2)
#         try:
#             await self.player.find_then_click(CLOSE_BUTTONS, timeout=2)
#             print("钻石不够，无法刷新任务")
#             return False
#         except FindTimeout:
#             return True




class RenWuLan300(RenWuLan):
    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._good_tasks = [
            'zuan_shi_ren_wu',
            'pi_jiu_4xing',
            'task_5star',
            'task_6star',
            'task_7star'
        ]
    
    async def run(self):
        await self._enter()
        await asyncio.sleep(3)
        await self._accept_all_tasks()

        if not await self._refresh_tasks():
            return

        end = False
        total_cost = 0
        max_num = 4
        while not end:
            task_num = len(await self.player.find_all_pos('receivable_task'))

            if task_num >= 3:
                # refresh tasks
                if not await self._refresh_tasks():
                    end = True
            else:
                # add tasks
                add_num = max_num - task_num
                total_cost += add_num
                await self._add_task(add_num)

            if self.player.is_exist('task_7star'):
                print("刷到了7星任务")
                end = True

            if not self.player.is_exist('receivable_task'):
                print("没有白信封了")
                end = True

            # accept tasks
            if not await self._accept_tasks():
                end = True
        
        print(f"总共消耗白信封：{total_cost}")

    async def _add_task(self, num):
        for _ in range(num):
            await self.player.click((290, 475))
        await asyncio.sleep(3)

    async def _refresh_tasks(self):
        await self.player.find_then_click('refresh4')
        await asyncio.sleep(2)
        try:
            await self.player.find_then_click(CLOSE_BUTTONS, timeout=2)
            print("钻石不够，无法刷新任务")
            return False
        except FindTimeout:
            return True