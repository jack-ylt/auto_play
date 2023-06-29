import asyncio

from lib.global_vals import *
from tasks.task import Task

class SheQvZhuLi(Task):
    """社区助理"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('community_assistant')

        # 75级解锁
        try:
            await self.player.monitor('gift')
        except FindTimeout:
            return

        if not await self._have_free_guess():
            return

        if not await self._found_right_assistant():
            return

        await self._play_guess_ring(max_num=4)
        await self.player.go_back_to('gift')
        await self._upgrade_Assistant()
        # TODO 如果没有升级，就不用送礼物
        if self._get_cfg('send_gift'):
            await self._send_gifts()

        self._increate_count('count', 1)

    def test(self):
        return self._get_cfg('enable') and self._get_count() <= 1

    async def _have_free_guess(self):
        try:
            await self.player.monitor('ring', timeout=1)
        except FindTimeout:
            self.logger.debug("Skip, free guess had been used up.")
            return False
        return True

    async def _found_right_assistant(self):
        """从上往下，找到第一个未满级的助理"""
        x = 50
        y_list = [240, 330, 175, 265, 365]
        for i, y in enumerate(y_list):
            try:
                # 达到60级，且满了，才看下一个
                await self.player.monitor('level_60', threshold=0.9, timeout=1)
                await self.player.monitor('level_full', threshold=0.9, timeout=1)
                if i == 2:
                    await self.player.drag((55, 380), (55, 90), speed=0.02)
                    await asyncio.sleep(1)
                await self.player.click((x, y), delay=2)
            except FindTimeout:
                break

        try:
            await self.player.monitor('ring', timeout=1)
        except FindTimeout:
            self.logger.info("need buy the assistant first.")
            return False

        return True

    async def _play_guess_ring(self, max_num=4):
        await self.player.find_then_click('ring')
        await self._click_cup()

        for _ in range(max_num - 1):
            # 有些平台，在新设备登陆，又需要重新勾选“跳过动画”
            name = await self.player.find_then_click(['tiao_guo_dong_hua', 'next_game'])
            if name == 'tiao_guo_dong_hua':
                await self.player.find_then_click('next_game')

            await asyncio.sleep(2)
            name, _ = await self.player.monitor(['cup', 'close', 'next_game'])
            if name == 'cup':
                await self._click_cup()
            elif name == 'close':
                await self.player.find_then_click('close')
            else:
                return

    async def _click_cup(self):
        # cup 点一次不一定管用，尤其是有动画的情况下
        for _ in range(5):
            name, pos = await self.player.monitor(['cup', 'next_game'])
            if name == 'cup':
                await self.player.click(pos)
                await asyncio.sleep(2)
            else:
                return

    async def _upgrade_Assistant(self):
        await self.player.click((800, 255))    # 一键领取所有爱心

        try:
            await self.player.find_then_click('have_a_drink', timeout=1)
        except FindTimeout:
            pass

        await self.player.monitor('gift')

        # try:
        #     # TODO 0.98 也不行，还是可能会误判
        #     await self.player.monitor('level_full', threshold=0.92, timeout=2)
        # except FindTimeout:
        #     return

        for _ in range(10):
            await self.player.click((820, 75))    # 升级
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=2)
            except FindTimeout:
                break

    async def _send_gifts(self):
        await self.player.find_then_click('gift')
        await self.player.monitor('send', verify=True)    # 避免turntable find误判

        pos_select_gift = (70, 450)
        pos_send_gift = (810, 450)

        # 转转盘
        while True:
            try:
                await self.player.find_then_click('turntable', timeout=2)
            except FindTimeout:
                break
            await self.player.click(pos_send_gift)
            await asyncio.sleep(2)
            await self.player.find_then_click('start_turntable')
            await asyncio.sleep(5)

            # 等待转盘明确结束
            for _ in range(5):
                try:
                    await self.player.monitor('start_turntable', timeout=1, verify=False)
                except FindTimeout:
                    break
                await asyncio.sleep(1)

        # 送其它礼物
        while True:
            await self.player.click(pos_select_gift, delay=0.2)
            await self.player.click(pos_send_gift)
            try:
                await self.player.find_then_click('close_btn1', timeout=1)
                break
            except FindTimeout:
                pass
