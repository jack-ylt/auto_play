import asyncio

from lib.global_vals import *
from tasks.task import Task



class RenWu(Task):
    """任务"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('task')
        await self.player.find_then_click('receive_all')

        try:
            await self.player.monitor('yi_ling_qv', threshold=0.9, timeout=1)
            self._increate_count('count')
            # 所有任务完成，就没必要再执行KuaiJieZhiNan了
            self._increate_count('count', val=1, cls_name='KuaiJieZhiNan')
        except FindTimeout:
            pass

    def test(self):
        return self.cfg['RenWu']['enable'] and self._get_count() < 1
