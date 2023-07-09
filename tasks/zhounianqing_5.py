from lib.global_vals import *
from tasks.task import Task
import asyncio


class ZhouNianQing5(Task):
    """周年庆5"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def test(self):
        return self._get_cfg('enable') and self._get_count() < 1

    async def run(self):
        if not self.test():
            return

        if not self.exist('zhou_nian_qing_5'):
            return
        
        await self.click('zhou_nian_qing_5')

        await asyncio.sleep(3)
        name, _ = await self.find(['mei_ri_qiandao', 'dian_zan_5'])
        if name == 'dian_zan_5':
            await self.click('dian_zan_5')
            # await self.click('cha_5')    # 可能被挡住
            await self.click((810, 70))
  
        await self.click('mei_ri_qiandao')

        name, _ = await self.find(['qiandao', 'yi_qiandao'])
        if name == 'qiandao':
            await self.click('qiandao')

        self._increate_count()
