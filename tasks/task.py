

import asyncio
import math

from lib.player import FindTimeout


class Task(object):
    def __init__(self, player, role_setting, counter):
        self.player = player
        self.logger = self.player.logger
        self._back_btn = (30, 60)
        self.cfg = role_setting
        self.counter = counter

    def test(self):
        raise NotImplementedError()

    async def run(self):
        raise NotImplementedError()

    async def _fight(self):
        """do fight, return win or lose"""
        if not await self.player.click_untile_disappear(['start_fight', 'fight1']):
            self.logger.warning("skip, click fight1 or start_fight failed")
            return 'lose'
        await asyncio.sleep(3)
        res = await self._do_fight()
        pos_ok = (430, 430)
        await self.player.click(pos_ok)
        return res

    async def _do_fight(self):
        name_list = ['win', 'lose', 'fast_forward1', 'go_last']
        while True:
            name = await self.player.find_then_click(name_list, threshold=0.9, timeout=10)
            if name in ['win', 'lose']:
                return name

    async def _move_to_left_top(self):
        self.logger.debug('_move_to_left_top')
        p1 = (200, 250)
        p2 = (600, 350)
        for i in range(3):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('dismiss_hero', timeout=1)
                return
            except FindTimeout:
                pass

    async def _move_to_right_top(self):
        self.logger.debug('_move_to_right_top')
        p1 = (550, 250)
        p2 = (150, 350)
        for i in range(3):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('warriors_tower', timeout=1)
                return
            except FindTimeout:
                pass

    async def _move_to_center(self):
        self.logger.debug('_move_to_center')
        await self._move_to_left_top()
        p1 = (450, 300)
        p2 = (200, 300)
        await self.player.drag(p1, p2)

    async def _move_to_left_down(self):
        self.logger.debug('_move_to_left_down')
        p1 = (150, 350)
        p2 = (550, 150)

        for i in range(3):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('market', timeout=1)
                return
            except FindTimeout:
                pass

    async def _move_to_right_down(self):
        self.logger.debug('_move_to_right_down')
        p1 = (650, 350)
        p2 = (150, 200)
        for i in range(5):
            await self.player.drag(p1, p2, speed=0.02)
            try:
                await self.player.monitor('bottom_right', timeout=1)
                return
            except FindTimeout:
                pass
        raise FindTimeout()

    def _merge_pos_list(self, btn_list, icon_list, dx=1000, dy=1000):
        def _is_close(p1, p2):
            x1, y1 = p1
            x2, y2 = p2
            # dy不试用绝对值，因为按钮一般在图标的下面
            if math.fabs(x1 - x2) <= dx and 0 <= y1 - y2 <= dy:
                return True
            return False

        merge_set = set()
        for p1 in btn_list:
            for p2 in icon_list:
                if _is_close(p1, p2):
                    merge_set.add(p1)
        merge_list = sorted(list(merge_set), key=lambda pos: pos[1])
        print(f"merge_list: {merge_list}")
        return merge_list

    async def _equip_team(self):
        await self.player.monitor('start_fight')    # 确保界面刷出来
        try:
            await self.player.monitor(['empty_box', 'empty_box5'], timeout=1)
        except FindTimeout:
            return

        x = 120
        y = 450
        dx = 65
        pos_list = [(x, y)]
        for _ in range(5):
            x += dx
            pos_list.append((x, y))

        await self.player.multi_click(pos_list)

    async def _equip_team_yjmk(self):
        await self.player.monitor('start_fight')    # 确保界面刷出来
        try:
            await self.player.monitor('empty_box3', timeout=1)
        except FindTimeout:
            return

        x = 150
        y = 400
        dx = 75
        pos_list = [(x, y)]
        for _ in range(5):
            x += dx
            pos_list.append((x, y))

        await self.player.multi_click(pos_list)

    def _get_count(self, key='count', cls_name=None, default=0):
        if self.counter is None:
            return 0

        if cls_name is None:
            cls_name = self.__class__.__name__
        return self.counter.get(cls_name, key, default=default)

    def _increate_count(self, key='count', val=1, cls_name=None, validity_period=1):
        if self.counter is None:
            return None

        if cls_name is None:
            cls_name = self.__class__.__name__
        new_val = self._get_count(key) + val
        self.counter.set(cls_name, key, new_val, validity_period=validity_period)

    def _set_count(self, val, key='count', cls_name=None, validity_period=1):
        if self.counter is None:
            return None

        if cls_name is None:
            cls_name = self.__class__.__name__
        self.counter.set(cls_name, key, val, validity_period=validity_period)

    def _get_cfg(self, *keys, cls_name=None):
        if cls_name is None:
            cls_name = self.__class__.__name__
        val = self.cfg[cls_name]
        for k in keys:
            val = val[k]
        return val

    # ----------- 以下是重构后的新函数 ------------
    # TODO 后续 player 替换成 player2

    async def click(self, targets, timeout=10, interval=1, until_disappear=True):
        """点击目标
        
        pos: 直接点击
        name: 先find, 再点击
        names: 先find (匹配度最高的), 再点击
        """
        if len(targets) == 2 and isinstance(targets[0], int) and isinstance(targets[1], int):
            await self.player.click(targets)
        else:
            if until_disappear:
                await self.player.click_untile_disappear(targets)
            else:
                await self.player.find_then_click(targets, timeout=timeout, delay=interval)

    async def find(self, target, timeout=10):
        """查找目标
        
        return name, pos
        """
        return await self.player.monitor(target, timeout=timeout)
    
    async def find_all(self, targes):
        """查找所有目标
        
        return pos_list
        """
        return await self.player.find_all_pos(targes)
    
    def exist(self, targets):
        """判断目标是否存在
        
        return True/False
        """
        return self.player.is_exist(targets)