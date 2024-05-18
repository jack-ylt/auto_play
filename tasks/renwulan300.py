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

GOOD_TASKS = [
            'diamond3',
            'pi_jiu2',
            'task_5star',
            'task_6star',
            'task_7star'
        ]


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
        
        try:
            await self._accept_all_tasks()
        except NoEnoughHero as e:
            return
        
        await self._finish_all_tasks()
        
        end = False
        while not end:
            try:
                await self._get_new_tasks(4)
            except NoEnoughXinFeng as e:
                end = True
                            
            if self.exist('task_7star'):
                print("刷到了7星任务")
                end = True

            try:
                await self._accept_tasks(GOOD_TASKS)
            except NoEnoughHero as e:
                end = True

            await self._finish_free_tasks()

            if len(await self.find_all('receivable_task')) >= 3:
                if not self.exist('shua_xing_40'):
                    print("任务数量超过4个了，可能会漏过一些好任务")
                    raise Exception()
                try:
                    await self._refresh_tasks()
                except NoEnoughZuanShi as e:
                    end = True

        

    async def _finish_all_tasks(self):
        # vip finish, finish tasks below 5 stars
        await self.click('one_click_collection2')
        try:
            await self.click(OK_BUTTONS, timeout=2)
            await asyncio.sleep(2)
            await self.click(OK_BUTTONS)
        except FindTimeout:
            pass

        # finish tasks below and above 5 stars
        for _ in range(15):
            pos_list = await self.player.find_all_pos(['finish_btn', 'diamond_0'])
            if pos_list:
                await self.click(sorted(pos_list)[0])
                await self.click(OK_BUTTONS)
                # 5星以上任务，会有两个ok确认
                try:
                    await self.click(OK_BUTTONS, timeout=2)
                except FindTimeout:
                    pass
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

    
    async def _get_new_tasks(self, nums=4):
        pos_list = await self.find_all('receivable_task')
        n = len(pos_list)
        if n >= nums:
            return
        else:
            for _ in range(nums - n):
                await self.click('bai_xin_feng')
            # 等待界面稳定，避免后续的点击误判
            await asyncio.sleep(2)


    async def _finish_free_tasks(self):
        while True:
            pos_list = await self.player.find_all_pos('diamond_0')
            if pos_list:
                await self.player.click(sorted(pos_list)[0])
                await self.player.find_then_click(OK_BUTTONS)
            else:
                break
