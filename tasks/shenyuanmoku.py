import asyncio

from lib.global_vals import *
from tasks.task import Task



class ShenYuanMoKu(Task):
    """深渊魔窟"""

    # 不需要用到 role和counter
    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._move_to_right_down()
        await self.player.click((635, 350))

        if not await self._enter():
            return False

        while True:
            if await self._have_good_skills():
                return True
            await self._exit()
            await self._enter()

    def test(self):
        # return self.cfg['ShenYuanMoKu']['enable']
        return True

    async def _enter(self):
        try:
            await self.player.monitor('ranking_icon4')
            await asyncio.sleep(1)
            await self.player.click((550, 435))
            await self.player.find_then_click('skill_preview_btn', timeout=3)
        except FindTimeout as e:
            self.logger.info("The shen yuan mo ku is not open yet.")
            return False
        else:
            return True

    async def _have_good_skills(self):
        # 有有舍有得，且在前三
        try:
            _, pos = await self.player.monitor('you_she_you_de', timeout=1)
        except FindTimeout:
            return False
        else:
            if pos[1] > 360:    # 不是在前三个
                return False

        # 有两个加120速度的技能
        # 且有给敌人加20%暴击率的技能
        seen = set()
        search_list = ['su_zhan_su_jue', 'feng_chi_dian_che']
        count = 0
        while count < 2:
            try:
                name, _ = await self.player.monitor(search_list, timeout=1)
            except FindTimeout:
                await self._swip_down()
                count += 1
            else:
                seen.add(name)
                search_list.remove(name)

        self.logger.debug(str(seen))
        # if 'bao_ji_20' not in seen:
        #     return False
        if 'su_zhan_su_jue' in seen:
            # TODO 移到上面体验会更好
            # TODO 备用技能可配置
            for _ in range(2):
                await self._swip_up()
            return True
        return False

    async def _swip_down(self):
        await self.player.drag((630, 430), (630, 80), speed=0.02, stop=True)

    async def _swip_up(self):
        await self.player.drag((630, 150), (630, 430), speed=0.01, stop=False)

    async def _exit(self):
        pos_list = await self.player.find_all_pos(CLOSE_BUTTONS)
        await self.player.click(sorted(pos_list)[0])
        await self.player.find_then_click(CLOSE_BUTTONS)
