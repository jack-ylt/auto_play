import asyncio

from lib.global_vals import *
from tasks.task import Task



class GongHuiZhan(Task):
    """打公会战宝箱"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        if not await self._enter_ghz():
            return

        await self._pull_up_the_lens()

        list1 = ['bao_xiang_guai', 'bao_xiang_guai1',
                 'bao_xiang_guai2', 'bao_xiang_guai3']
        list2 = ['guai1', 'guai2', 'guai3', 'guai4', 'guai5', 'guai6', 'guai7']
        bao_xiang_guai_list = list1 + list2

        for _ in range(10):
            # 确保回到公会战主界面
            await self.player.click_untile_disappear(CLOSE_BUTTONS)
            await self.player.monitor('zhu_jun_dui_wu')
            try:
                await self.player.find_then_click(bao_xiang_guai_list, threshold=0.85, timeout=2, cheat=False)
            except FindTimeout:
                break
            else:
                res = await self._tiao_zhan()
                if res == 'no_hero':
                    self._increate_count()
                    return

        # TODO 银行可能没有在画面中

    def test(self):
        return self._get_cfg('enable') and self._get_count('count') < 1

    async def _enter_ghz(self):
        try:
            await self.player.find_then_click('ju_dian_ghz', timeout=1)
            await self.player.monitor('huang_shui_jing')    # 可能没加公会
        except FindTimeout:
            return False

        await self.player.monitor('huang_shui_jing')

        try:
            # 休整期、结算期，没必要进去
            await self.player.monitor(['xiu_zheng', 'jie_suan_qi'], timeout=1)
            return False
        except FindTimeout:
            pass

        try:
            await self.player.find_then_click('enter1', timeout=1)
        except FindTimeout:
            # 没有enter1，可能是还在报名期
            return False

        await asyncio.sleep(5)
        await self.player.monitor(['jidi'] + CLOSE_BUTTONS, timeout=20)

        # 进入后，可能有4种情况：
        # - 设置阵容
        # - 保存整容
        # - 通知
        # - 直接看到基地

        # TODO 利兹可能会出来 （概率应该很低）
        await asyncio.sleep(1)
        name, pos = await self.player.monitor(['bao_cun', 'jidi', 'she_zhi_zhen_rong'] + CLOSE_BUTTONS, timeout=1)
        if name == 'bao_cun':
            # 第一次进入，要保存阵容
            await self.player.click(pos)
            await self.player.find_then_click(OK_BUTTONS)
            await asyncio.sleep(5)
            await self.player.monitor('jidi', timeout=20)
        elif name == 'she_zhi_zhen_rong':
            try:
                await self.player.find_then_click('bao_cun', timeout=1)
            except FindTimeout:
                await self.player.click(pos)
                await self.player.find_then_click('bao_cun')
            await self.player.find_then_click(OK_BUTTONS)
            await asyncio.sleep(5)
            await self.player.monitor('jidi', timeout=20)

            # tuo guan
            await self.player.find_then_click('zhu_jun_dui_wu')
            await self.player.find_then_click('yi_jian_tuo_guan')
            await self.player.find_then_click(OK_BUTTONS)
            await self.player.find_then_click(CLOSE_BUTTONS)
        elif name in CLOSE_BUTTONS:
            await self.player.click(pos)

        asyncio.sleep(1)
        return True

    async def _pull_up_the_lens(self):
        _, pos = await self.player.monitor('jidi')
        for _ in range(5):
            await self.player.scrool_with_ctrl(pos)
            try:
                await self.player.monitor('jidi_small', timeout=1, threshold=0.9)
                return True
            except FindTimeout:
                await asyncio.sleep(1)
                continue
        return False

    async def _tiao_zhan(self):
        """return lose, no_hero, or done"""
        await self.player.monitor(['dead', 'tiao_zhan', 'tiao_zhan1'])

        for pos in await self.player.find_all_pos(['tiao_zhan', 'tiao_zhan1']):
            try:
                # 确保不会点错
                await self.player.monitor(['tiao_zhan', 'tiao_zhan1'])
                await self.player.click(pos)
                res = await self._do_fight()
            except FindTimeout:
                # 怪物可能是被别人抢了
                return 'done'

            # 胜利就继续，否则退出
            if res != 'win':
                return res

        await self._swip_up()

        for pos in await self.player.find_all_pos(['tiao_zhan', 'tiao_zhan1']):
            try:
                # 确保不会点错
                await self.player.monitor(['tiao_zhan', 'tiao_zhan1'])
                await self.player.click(pos)
                res = await self._do_fight()
            except FindTimeout:
                # 怪物可能是被别人抢了
                return 'done'

            # 胜利就继续，否则退出
            if res != 'win':
                return res

        await self.player.find_then_click(CLOSE_BUTTONS)    # 确保关闭挑战界面
        return 'done'

    async def _do_fight(self):
        await self.player.monitor('dui_wu_xiang_qing')
        name, pos = await self.player.monitor(['checked_box', 'check_box'])
        if name == 'check_box':
            await self.player.click(pos)

        try:
            await self.player.find_then_click('tiao_zhan_start', timeout=1)
        except FindTimeout:
            await self.player.find_then_click(CLOSE_BUTTONS)
            return 'no_hero'

        try:
            name, _ = await self.player.monitor(['win', 'lose'])
        except FindTimeout:
            # 敌人可能已死亡
            await self.player.find_then_click(CLOSE_BUTTONS)
            return 'win'

        # await self.player.find_then_click(OK_BUTTONS)
        # ok 经常点击失效
        await self.player.click_untile_disappear(OK_BUTTONS)
        return name

    async def _swip_up(self):
        top = (400, 150)
        down = (400, 450)
        await self.player.drag(down, top, speed=0.02, stop=True)

    async def _move_bank_center(self):
        center_pos = (430, 260)
        _, bank_pos = await self.player.monitor('bank_small')
        await self.player.drag(bank_pos, center_pos, speed=0.05, stop=True)
