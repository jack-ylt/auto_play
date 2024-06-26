import asyncio

from lib.global_vals import *
from tasks.task import Task



class YiJiMoKu(Task):
    """遗迹魔窟

    适用于高级号，扫荡收菜
    TODO: 针对没有达到15关的小号，也收菜
    """

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        if not await self._enter():
            return False

        self._increate_count()

        # 领取资源
        await self.player.find_then_click('yi_jian_ling_qv2')
        try:
            await self.player.find_then_click(OK_BUTTONS, timeout=3)
        except FindTimeout:
            # 打通的关数太少，是没有菜可以收的
            # 或者已经领过了
            # TODO 要以get_count为准，要区分小号和大号，因为可能购物过程出错退出，需要重新购物
            # return
            pass

        lack_gold = False

        # 普通商店购物
        try:
            # 小号可能还没有购物车
            await self.player.find_then_click('gou_wu_che')
        except FindTimeout:
            return
        await self.player.find_then_click('pu_tong_shang_dian')
        await self.player.monitor('ptsd_title')

        finish_buy = False    # 东西是否都买完了，可以结束了

        while True:
            # gold2 包含了按钮花纹，而按钮花纹会因为位置不同而不同，影响识别率
            # list1 = await self.player.find_all_pos('gold2')
            list1 = await self.player.find_all_pos('gold3')
            list2 = await self.player.find_all_pos(['zhuan_pan_bi', 'jing_ji_men_piao'])
            pos_list = self._merge_pos_list(list1, list2, dy=(0, 30))

            if pos_list:
                await self.player.click(pos_list[0], cheat=False)
                try:
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                except FindTimeout:
                    # 如果金币不足，结束
                    lack_gold = True
                    break
            else:
                if finish_buy:
                    break
                reach_bottom = await self.player.drag_then_find((350, 450), (350, 180), 'reach_bottom')
                if reach_bottom:
                    finish_buy = True

        await self.player.find_then_click(CLOSE_BUTTONS)

        # 高级商店购物
        lack_diamond = False
        await self.player.find_then_click('gao_ji_shang_dian')
        await self.player.monitor('gjsd_title')

        goods_list = ['pi_jiu']
        if self._get_cfg('mai_bao_tu'):
            goods_list.append('bao_tu_moku')
        if self._get_cfg('mai_hui_zhang'):
            goods_list.append('hui_zhang_moku')

        finish_buy = False    # 东西是否都买完了，可以结束了

        while True:
            if not lack_gold and self.player.is_exist('gold2'):
                await self.player.find_then_click('gold2', cheat=False)
                try:
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                    continue
                except FindTimeout:
                    lack_gold = True

            if not lack_diamond:
                # # buy_btn 识别率太低
                # list1 = await self.player.find_all_pos('buy_btn')
                pos_list = await self.player.find_all_pos(goods_list)
                # pos_list = self._merge_pos_list(list1, list2, dy=30)
                if pos_list:
                    pos = pos_list[0]
                    pos = (pos[0] + 340, pos[1] + 20)
                    await self.player.click(pos)
                    # fix 魔窟没有 lack_of_diamond
                    try:
                        await self.player.monitor('ok8', timeout=3)
                    except FindTimeout:
                        lack_diamond = True
                    else:
                        await self.player.find_then_click(OK_BUTTONS)
                        await self.player.find_then_click(OK_BUTTONS)
                        continue                   

            if finish_buy:
                break

            # # 没东西可以买了(金币、钻石都没可买的），向上滑动
            reach_bottom = await self.player.drag_then_find((350, 450), (350, 180), 'reach_bottom')
            if reach_bottom:
                # 达到了底部，不能立即结束，有可能还有东西需要买的
                finish_buy = True

        await self.player.find_then_click(CLOSE_BUTTONS)

        self._increate_count(validity_period=4)

    def test(self):
        return self._get_cfg('enable') and self._get_count() < 1

    async def _enter(self):
        await self._move_to_right_down()
        await self.player.click((635, 350))
        name, _ = await self.player.monitor(['close', 'jin_ru', 'hou_kai_qi', 'yi_jian_ling_qv2'])
        if name == 'close':
            await self._equip_team_yjmk()
            await self.player.click_untile_disappear('start_fight')
            return True
        elif name == 'hou_kai_qi':
            # 活动未开启
            return False
        elif name == 'yi_jian_ling_qv2':
            # 一点就进来了是太小的小号
            return False
        elif name == 'jin_ru':
            await self.player.click((110, 435))    # click enter btn
            name, _ = await self.player.monitor(['ying_xiong_chu_zhan', 'yi_jian_ling_qv2', 'huo_dong_wei_kai_qi', 'close', 'kai_shi_tiao_zhan'])
            if name == 'huo_dong_wei_kai_qi':
                return False
            elif name == 'yi_jian_ling_qv2':
                return True
            elif name == 'ying_xiong_chu_zhan':
                # 小号
                await self._equip_team_yjmk()
                await self.player.click_untile_disappear('start_fight')
                return True
            elif name in ['close', 'kai_shi_tiao_zhan']:
                # 长时间未登录，会有新手引导
                await self.player.find_then_click('close', timeout=2, raise_exception=False)
                await self.player.find_then_click('kai_shi_tiao_zhan')
                await self.player.find_then_click(OK_BUTTONS)
                await self.player.monitor('close')
                await self._equip_team_yjmk()
                await self.player.click_untile_disappear('start_fight')
                return True
