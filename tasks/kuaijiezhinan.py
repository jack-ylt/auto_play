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

        await self.player.find_then_click(['quick_ico', 'quick_ico1'])
        if not await self.player.click_untile_disappear('yi_jian_zhi_xing'):
            return
        
        try:
            await self.player.monitor(['ok_1', 'sao_dang_zhong'], timeout=3)
        except FindTimeout:
            pass
        else:
            await self._update_counter()
            # 等待时间长也没什么用，挑战副本有时候就是没有满，是官方的bug
            await asyncio.sleep(5)
            await self.player.find_then_click('ok_1')
        finally:
            await self.player.find_then_click(CLOSE_BUTTONS)
            # self._increate_count()

    def test(self):
        return self._get_cfg() and self._get_count() < 1

    async def _update_counter(self):
        self._increate_count('count', val=3, cls_name='XianShiJie')
        self._increate_count('count', val=2, cls_name='XingYunZhuanPan')
        self._increate_count('count', val=6, cls_name='TiaoZhanFuben')
        self._increate_count('count', val=3, cls_name='WuQiKu')
        self._increate_count('count', val=3, cls_name='JingJiChang')
        self._increate_count('count', val=2, cls_name='XingCunJiangLi')
