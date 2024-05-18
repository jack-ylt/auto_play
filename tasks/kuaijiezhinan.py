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
        await self.click('ok_1', until_disappear=True)

        # 游戏有bug，一次不一定能完成所有任务，所以多点一次
        await asyncio.sleep(5)
        await self.click('yi_jian_zhi_xing')
        await self.click('ok_1')

        self._update_counter()

        # 是否完成了，要看是否完成了所有日常任务
        # 详见renwu.py
        # self._increate_count()

    def test(self):
        return self._get_cfg() and self._get_count() < 1

    def _update_counter(self):
        # 100级以上，就可以执行快捷指南了，后续很多个任务就没必要执行了。
        self._increate_count('count', val=3, cls_name='XianShiJie')
        self._increate_count('count', val=2, cls_name='XingYunZhuanPan')
        self._increate_count('count', val=6, cls_name='TiaoZhanFuben')
        self._increate_count('count', val=3, cls_name='WuQiKu')
        self._increate_count('count', val=3, cls_name='JingJiChang')
        self._increate_count('count', val=2, cls_name='XingCunJiangLi')
        