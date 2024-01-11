import asyncio

from lib.global_vals import *
from tasks.task import Task


class KuaiJieZhiNan(Task):
    """快捷每日任务"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.click(['quick_ico', 'quick_ico1'])
        await self.find('jin_xing_pu_tong_yao_qing')

        await self.click('yi_jian_zhi_xing')
        await asyncio.sleep(5)
        await self.click('ok_1')

        # 游戏有bug，一次不一定能完成所有任务，所以多点一次
        await asyncio.sleep(5)
        await self.click('yi_jian_zhi_xing')
        await self.click('ok_1')

        self._update_counter()
        self._increate_count()

    def test(self):
        return self._get_cfg() and self._get_count() < 1

    def _update_counter(self):
        for name in ['XianShiJie', 'XingYunZhuanPan', 'TiaoZhanFuben', 'WuQiKu', 'JingJiChang', 'XingCunJiangLi']:
            self._increate_count('count', val=1, cls_name=name)
