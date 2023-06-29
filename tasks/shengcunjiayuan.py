import asyncio

from lib.global_vals import *
from tasks.task import Task



class ShengCunJiaYuan(Task):
    """生存家园"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count() >= 1

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_top()
        await self.player.find_then_click('survival_home')
        await self._collect_resouces()

        await self.player.click_untile_disappear('fight_btn')

        await self._collect_all_boxes()    # fight 有可能失败，比如点到基地

        if self._get_cfg('fight_boss'):
            await self._fight_home_boos()

        await self._collect_all_boxes()

        self._increate_count()

    def test(self):
        return self._get_cfg('enable')

    async def _collect_resouces(self):
        await self.player.monitor('zhu_ji_di')
        await asyncio.sleep(3)    # 点太快，可能卡住
        try:
            await self.player.find_then_click('resources', timeout=1)
        except FindTimeout:
            pass

    async def _fight_home_boos(self):
        kill_count = self._get_count()
        max_fight = min(5, (9 - kill_count))    # 一天最多9次
        win_count = 0

        if max_fight <= 0:
            return

        total_floors = await self._get_total_floors()

        # 从高层往低层打，战力高的话，可能多得一些资源
        # 战力低得话，可能就要浪费一些粮食了
        for i in range(total_floors, 3, -1):
            await self._goto_floor(i)    # 注：不一定每次进来就直接第7层，所以还是需要_goto_floor
            for d in [None, 'left_top', 'left_down', 'right_down', 'right_top']:
                await self.player.monitor('switch_map')
                await asyncio.sleep(1)    # 怪物刷新出来有点慢
                if d:
                    # 先在当前视野找boos，然后再上下左右去找
                    await self._swip_to(d)
                if await self._find_boos():
                    win = await self._fight()
                    if not win:
                        self.logger.warning(f"Fight lose, in floor: {i}")
                        break
                    win_count += 1
                    self._increate_count()    # 记录杀的boos个数
                    if win_count >= max_fight:
                        self.logger.debug(
                            f"stop fight, reach the max figh count: {max_fight}")
                        return
                    if await self._reach_point_limit():
                        self.logger.debug(f"stop fight, _reach_point_limit")
                        return

    async def _collect_all_boxes(self):
        await self.player.monitor('switch_map')
        try:
            await self.player.find_then_click('collect_all_box', timeout=1)
        except FindTimeout:
            return

        try:
            await self.player.find_then_click('receive3', timeout=3)
        except FindTimeout:
            return    # 可能以及收集完了

    async def _get_total_floors(self):
        await self._open_map()

        locked_field = 0
        await self._drag_floors('up')
        map_list = await self.player.find_all_pos('locked_field')
        locked_field += len(map_list)
        if locked_field == 0:
            await self._close_map()
            return 7

        await self._drag_floors('down')
        map_list = await self.player.find_all_pos('locked_field')
        locked_field += len(map_list)

        if locked_field >= 5:
            # 第四层没有解锁的话，会被重复统计
            floors = 7 - locked_field + 1
        else:
            floors = 7 - locked_field

        await self._drag_floors('up')
        await self._close_map()
        return floors

    async def _open_map(self):
        for _ in range(3):
            await self.player.find_then_click('switch_map')
            await asyncio.sleep(1)
            try:
                await self.player.monitor(['ye_wai_di_tu', 'ye_wai_di_tu1', 'map_lock'], timeout=1)
                return
            except FindTimeout:
                continue

    async def _close_map(self):
        for _ in range(3):
            await self.player.find_then_click('switch_map')
            await asyncio.sleep(1)
            try:
                await self.player.monitor(['ye_wai_di_tu', 'ye_wai_di_tu1', 'map_lock'], timeout=1)
                continue
            except FindTimeout:
                return

    async def _drag_floors(self, d):
        pos1 = (55, 300)
        pos2 = (55, 400)
        if d == 'up':
            await self.player.drag(pos2, pos1, speed=0.02)
        elif d == 'down':
            await self.player.drag(pos1, pos2, speed=0.02)
        await asyncio.sleep(1)

    async def _goto_floor(self, i):
        pos_map = {
            1: (50, 288),
            2: (50, 321),
            3: (50, 356),
            4: (50, 388),
            5: (50, 341),
            6: (50, 375),
            7: (50, 409)
        }

        await self._open_map()

        if i <= 4:
            await self._drag_floors('down')
        else:
            await self._drag_floors('up')

        await self.player.click(pos_map[i])

        await self._close_map()

    async def _swip_to(self, direction, stop=False):
        left_top = (150, 150)
        top = (400, 150)
        right_top = (700, 150)
        left = (150, 270)
        right = (700, 270)
        left_down = (150, 370)
        down = (400, 370)
        right_down = (700, 370)

        swip_map = {
            'left_top': (left_top, right_down),
            'left_down': (left_down, right_top),
            'right_down': (right_down, left_top),
            'right_top': (right_top, left_down),
            'top': (top, down),
            'down': (down, top),
            'left': (left, right),
            'right': (right, left),
        }

        self.logger.debug('swipe_to {direction}')
        p1, p2 = swip_map[direction]
        await self.player.drag(p1, p2, speed=0.02, stop=stop)

    async def _find_boos(self):
        await self.player.monitor('switch_map')
        pos_list = await self.player.find_all_pos(['boss', 'boss1', 'boss2'])
        for pos in pos_list:
            p_center = (pos[0] + 40, pos[1] - 40)
            if self._can_click(p_center):
                await self.player.click(p_center)
                return True
        return False

    def _can_click(self, boss_pos):
        """确保在可点击区域"""
        x, y = boss_pos
        if x < 30 or x > 830:
            return False
        if y < 90 or y > 490:
            return False
        if x < 100 and y > 410:
            return False
        if x > 690 and y > 400:
            return False
        return True

    async def _fight(self, max_try=2):
        pos_go_last = (836, 57)

        await self.player.find_then_click('fight6')

        for _ in range(max_try):
            await self.player.find_then_click(['start_fight', 'xia_yi_chang1'])
            # 界面切换需要时间 （xia_yi_chang1 和 message 是在同一个页面的）
            await asyncio.sleep(2)

            for _ in range(24):
                name, _ = await self.player.monitor(['message', 'fight_report'])
                if name == 'message':
                    await self.player.click(pos_go_last)
                else:
                    break

            fight_res, _ = await self.player.monitor(['win', 'lose'], threshold=0.9)

            if fight_res == 'win':
                await self.player.find_then_click(OK_BUTTONS)
                return True

        await self.player.find_then_click(OK_BUTTONS)
        return False

    async def _reach_point_limit(self):
        # 如果达到了90或者95分，就不能再打boos了
        try:
            await self.player.monitor(['num_90', 'num_95'], threshold=0.9, timeout=1)
            return True
        except FindTimeout:
            return False
