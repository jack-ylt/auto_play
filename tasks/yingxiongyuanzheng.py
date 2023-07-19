import asyncio
from datetime import datetime
from lib.global_vals import *
from tasks.task import Task



class YingXiongYuanZheng(Task):
    """英雄远征"""

    # TODO 游戏如果在一个新设备登录，傻白就会出来，会卡住
    # 只有傻白的情况下点傻白
    # 出现手套，就要点手套
    # 都没有就可以esc

    # 如果是没有14星英雄的
    # 则可以点两次回退按钮退出（esc无效）

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        for _ in range(3):
            await self._enter()

            try:
                await self._collect_oil()
                await self.player.go_back_to('shang_dian')
                await self._yuan_gu_yi_ji_saodan()
                await self.player.go_back_to('shang_dian')
                await self._buy_goods()
                await self.player.go_back_to('shang_dian')
                if self._get_cfg('sweep') and datetime.now().weekday() % 2 == 0:
                    await self._saodan()
                return
            except FindTimeout:
                try:
                    await self.player.monitor(['no_14star_hero', 'hand1', 'sha_bai_left', 'sha_bai_right'], timeout=1)
                except FindTimeout:
                    raise
                else:
                    await self._handle_shabai()

    def test(self):
        return self.cfg['YingXiongYuanZheng']['enable']

    async def _enter(self):
        await self._move_to_right_top()
        await self.player.find_then_click('hero_expedition')
        await self.player.monitor('production_workshop')

    async def _handle_shabai(self):
        self.logger.warning('handle shabai')
        pos_back = (38, 63)
        for _ in range(10):
            try:
                name = await self.player.find_then_click(['no_14star_hero', 'hand1', 'sha_bai_left', 'sha_bai_right'], timeout=2, verify=False)
                if name == 'no_14star_hero':
                    # 这种情况esc没用的
                    return await self.player.click(pos_back)
                await asyncio.sleep(2)
            except FindTimeout:
                await self.player.go_back()
                try:
                    name, _ = await self.player.monitor(['hand1', 'sha_bai_left', 'sha_bai_right', 'setting'], timeout=2)
                    if name == 'setting':
                        # 可能多点了次esc，导致系统提示“是否退出游戏”
                        # TODO 最好让gamer来处理
                        await self.player.find_then_click(CLOSE_BUTTONS + ['zai_wan_yi_hui'], timeout=1, raise_exception=False)
                        return
                    else:
                        continue
                except FindTimeout:
                    await self.player.click(pos_back)

    # TODO 不同的平台可能不同，不应该耦合在一起，需要分别处理
    # 让gamer来处理吧
    async def _handle_first_login(self):
        self.logger.info("YingXiongYuanZheng: handle for first login.")

        await self.player.monitor(['hand', 'hand1'])
        await self.player.find_then_click('production_workshop')
        await self.player.find_then_click('sha_bai_left', timeout=3, verify=False, raise_exception=False)
        await self.player.go_back()

        await self.player.monitor('sha_bai_left')
        await self.player.find_then_click('yuan_zheng_fu_ben')
        await self.player.monitor('sha_bai_right')
        await self.player.click((280, 485))

        name, pos = await self.player.monitor(['bei_bao', 'close1'])
        if name == 'bei_bao':
            await asyncio.sleep(5)
            while True:
                await self.player.go_back()
                try:
                    await self.player.monitor('sao_dang', timeout=2)
                    break
                except FindTimeout:
                    await asyncio.sleep(2)
        else:
            await self.player.click(pos)

        await self.player.go_back()

        try:
            await self.player.monitor('sha_bai_left', timeout=2)
        except FindTimeout:
            return

        await self.player.find_then_click('production_workshop')
        await self.player.monitor('one_click_collection1')
        await self.player.go_back()

    async def _collect_oil(self):
        await self.player.find_then_click('production_workshop')
        await self.player.find_then_click('one_click_collection1')

    async def _saodan(self):
        await self.player.find_then_click('yuan_zheng_fu_ben')
        # 每个大关卡，扫荡有过场动画，可能需要多点几次
        await self.player.click_untile_disappear('sao_dang')
        # await self.player.find_then_click('sao_dang')
        await self.player.find_then_click('max1')
        await self.player.find_then_click(['sao_dang1', 'sao_dang3'])

    async def _buy_goods(self):
        await self.player.find_then_click('shang_dian')
        for _ in range(3):
            await self.player.find_then_click('men')
            if self.player.is_exist('yan_jiu_bi'):
                break
        else:
            # 需要通关4-10才行
            return

        list1 = await self.player.find_all_pos('yan_jiu_bi')
        list2 = await self.player.find_all_pos("ji_ying_zu_jian")
        pos_list1 = self._merge_pos_list(list1, list2, dx=50, dy=100)
        for pos in sorted(pos_list1, reverse=True):
            await self.player.click((pos[0]+30, pos[1]))
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=3)
                await self.player.find_then_click(OK_BUTTONS)
            except FindTimeout:
                break

    async def _yuan_gu_yi_ji_saodan(self):
        await self.player.find_then_click('yuan_zheng_fu_ben')
        await self.player.find_then_click('tiao_zhan_fu_ben2')
        try:
            await self.player.monitor('kao_gu_tong_xing_zheng')
        except FindTimeout:
            # 需要通关4-10才行
            return
        
        await self.player.find_then_click('plus2')    
        list1 = await self.player.find_all_pos('qi_you')
        list2 = await self.player.find_all_pos("kao_gu_tong_xing_zheng2")
        pos_list1 = self._merge_pos_list(list1, list2, dx=50, dy=100)
        for pos in sorted(pos_list1):
            await self.player.click((pos[0]+30, pos[1]))
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=3)
                await self.player.find_then_click(OK_BUTTONS)
            except FindTimeout:
                break
        await self.player.find_then_click(CLOSE_BUTTONS)

        await self.player.monitor('kao_gu_tong_xing_zheng')

        men_piao = self.player.get_text((390, 38, 470, 70))
        try:
            men_piao = int(men_piao.split('/')[0])
        except ValueError:
            men_piao = 0
        if men_piao == 0:
            return
        
        try:
            ji_fen = int(self.player.get_text((654, 170, 707, 200)))
        except ValueError:
            ji_fen = 0
        if ji_fen < 3000:
            if men_piao < 9:
                return
            else:
                num = men_piao
        else:
            num = 999
        
        await self.player.find_then_click('sao_dang')

        if num == 999:
            await self.player.find_then_click('max4')
        else:
            await self.player.find_then_click('1_saodan')
            number = num - 9
            if number < 10:
                await self.player.tap_key(str(number))
            else:
                await self.player.tap_key(str(number // 10))
                await self.player.tap_key(str(number % 10))
            await self.player.find_then_click('que_ding')

        await self.player.find_then_click(['sao_dang1', 'sao_dang3'])

        await self.player.find_then_click(OK_BUTTONS)
        await self.player.find_then_click('yuan_gu_mi_zang')
        _, (x,y) = await self.player.monitor('red_point3')
        await self.player.click((x-25, y+25))
        

    async def _exit(self):
        while True:
            name, pos = await self.player.monitor(['go_back', 'go_back1', 'go_back2', 'setting'])
            if name in ['go_back', 'go_back1', 'go_back2']:
                await self.player.click(pos)
            else:
                break
