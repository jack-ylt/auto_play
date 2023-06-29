import asyncio
import re
from datetime import datetime
from lib.global_vals import *
from tasks.task import Task




class GuanJunShiLian(Task):
    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self.zhan_li = None
        self.score = self._get_count('score')
        self.is_zuanshi = self._get_count('reach_zuanshi')
        self.fight_too_much = set()
        self.can_not_win = set()
        self.too_poor = set()
        self.min_ji_fen = 0

    def test(self):
        if not self._get_cfg('enable'):
            return False
        if not datetime.now().weekday() in (4, 5, 6):
            return False
        if self.score >= 50 and self.is_zuanshi:
            return False
        return True
    
    async def run(self):
        if not self.test():
            return

        await self._enter()

        while True:
            if self.player.is_exist("zuan_shi_duan_wei"):
                self.is_zuanshi = 1
                self._increate_count('reach_zuanshi', validity_period=4)

            if self.player.is_exist("huang_jin_duan_wei") and datetime.now().weekday() == 4:
                # 第一天就达到了黄金，此时分高的很少，即使辛苦打上去也很难上钻石，还很容易成为别人的踏脚石
                self.logger.info(f"reach huangjin and it's the first day, there are few rich player, so exit")
                break

            try:
                score = await self._fight()
                self.score += score
                self._increate_count('score', score, validity_period=4)
            except PlayException as err:
                if str(err) == "no opponment":
                    self.logger.info("no opponment, so exit")
                    break
                elif str(err) == "set team":
                    await self._set_team_defense()

            if self.score > 50 and self.is_zuanshi:
                self.logger.info(f"the score is {self.score} (>50) and has reached zuanshi, so exit")
                break

    async def _enter(self):
        self.logger.info('_enter')
        await self._move_to_left_top()
        await self.player.find_then_click('arena')
        await self.player.find_then_click('champion')
        await self.player.find_then_click('enter')

        name, _ = await self.player.monitor(['zhan_dou_shuo_ming', 'zhan_dou'])
        if name == 'zhan_dou':
            return True

        await self.player.find_then_click(CLOSE_BUTTONS)
        await self.player.find_then_click('save_1')

        try:
            await self.player.monitor('zhan_dou', timeout=3)
            return True
        except FindTimeout:
            return False

    async def _set_team_offense(self):
        self.logger.info('_set_team_offense')
        await self._set_team()

    async def _set_team_defense(self):
        self.logger.info('_set_team_defense')
        while not self.player.is_exist('zhan_dou'):
            await self.player.find_then_click(CLOSE_BUTTONS)
        await asyncio.sleep(1)
        await self.player.find_then_click("fang_shou_zheng_rong")
        await self._set_team()
        await self.player.find_then_click('save_1')

    async def _set_team(self):    
        # await self.player.find_then_click('fang_shou_zheng_rong')
        await self.player.monitor('ying_xiong_chu_zhan')

        # if self.player.is_exist('empty_box4'):
        cols = 3 if self.player.is_exist('lock_hero') else 6
        
        # 取消上阵英雄
        x_list = [212, 286, 390, 467, 544, 620]
        y_list = [230, 300, 370]
        for r in range(3):
            pos_list = [(x_list[c], y_list[r]) for c in range(cols)]
            await self.player.multi_click(pos_list) 

        # 重新上阵
        x, y = (72, 468)
        pos_list = [(x + 80 * c, y) for c in range(9)]
        await self.player.multi_click(pos_list) 
        if cols == 6:
            await self._swipe_left()
            await self.player.multi_click(pos_list) 

        # 1, 3 队互换
        await self.player.click((706, 228))
        await self.player.click((706, 370))
        # 2, 3 队互换
        await self.player.click((706, 297))
        await self.player.click((706, 370))

        # 更新战力
        area = (395, 153, 503, 183)
        self.zhan_li = int(self.player.get_text(area, format='number'))
        
    async def _swipe_left(self):
        p1 = (720, 470)
        p2 = (5, 470)
        await self.player.drag(p1, p2, speed=0.001, stop=True, step=1000)


    async def _fight(self):
        self.logger.info('_fight')
        try:
            await self.player.monitor('zhan_dou')
            # 获取积分太不准了 555
            # ji_fen_me = await self._get_my_score()
            await self.player.find_then_click('zhan_dou')
        except FindTimeout:
            raise PlayException("set team")

        await self.player.monitor('ying_xiong_chu_zhan')
        try:
            await self.player.monitor('men_piao_3', timeout=3)
        except FindTimeout:
            raise PlayException("set team")
        
        for _ in range(5):
            for j in range(3):
                zhan_li = await self._get_enemy_power(j)
                if zhan_li in self.fight_too_much or zhan_li in self.can_not_win:
                    continue
                if zhan_li > await self._get_self_power() * 1.2:
                    continue

                # 如果积分太低，后面的人只会更低 (不一定)
                # 没到钻石之前，要打积分够多的人，节约门票
                ji_fen_enemy = await self._get_enemy_score(j)
                
                if not self.is_zuanshi:
                    if zhan_li in self.too_poor:
                        continue
                    
                    if ji_fen_enemy < self.min_ji_fen:
                        continue

                try:
                    score = await self._do_fight(j)
                    if score == 1:
                        self.can_not_win.add(zhan_li)

                    ji_fen_add = await self._get_increace_score()
                    print('ji_fen_add', ji_fen_add)
                    if ji_fen_add < 10:
                        self.too_poor.add(zhan_li)
                        self.min_ji_fen = max(self.min_ji_fen, ji_fen_enemy)
                    await self.player.find_then_click(OK_BUTTONS)

                    return score
                except PlayException as err:
                    if str(err) == "reach max fight num":
                        self.fight_too_much.add(zhan_li)
                        continue
                    else:
                        raise
    
            await self._reflash()
        raise PlayException("no opponment")
            
    async def _get_my_score(self):
        # area = (610, 205, 720, 235)
        # 之圈数字，否则容易误识别
        area = (668, 205, 720, 235)
        ji_fen = int(self.player.get_text(area, format='number'))
        self.logger.info(f"_get_my_score: {ji_fen}")
        return ji_fen
    
    async def _get_enemy_score(self, idx):
        areas = [
            (430, 246, 495, 280),
            (430, 327, 495, 362),
            (430, 409, 495, 444),
        ]
        ji_fen = int(self.player.get_text(areas[idx], format='number'))
        self.logger.info(f"_get_enemy_score: {ji_fen}")
        return ji_fen

    async def _get_enemy_power(self, idx):
        areas = [
            (239, 250, 360, 280),
            (239, 330, 360, 360),
            (239, 415, 360, 445),
        ]
        zhan_li = int(self.player.get_text(areas[idx], format='number'))
        self.logger.info(f"_get_enemy_power: {zhan_li}")
        return zhan_li
    
    async def _get_self_power(self):
        if self.zhan_li:
            return self.zhan_li
        
        try:
            await self.player.find_then_click('zhan_dou_3')
        except FindTimeout:
            raise PlayException("set team")

        await self.player.monitor(['fight_green', 'fight_green_1'])

        area = (395, 153, 503, 183)
        zhan_li = int(self.player.get_text(area, format='number'))
        self.zhan_li = zhan_li

        await self.player.find_then_click(CLOSE_BUTTONS)
        
        self.logger.info(f"_get_self_power: {zhan_li}")
        return zhan_li
    
    async def _get_increace_score(self):
        area = (220, 335, 335, 370)
        text = self.player.get_text(area)
        # 1474(+23)
        m = re.search(r'\(\+(\d+)\)', text)
        if m:
            score = int(m.group(1))
            self.logger.info(f"_get_increace_score: {score}")
            return score
        else:
            # 识别不成功，或者是负的
            return 0
        
    async def _reflash(self):
        # 刷新页面，并等待刷新完成
        await self.player.find_then_click('shua_xing')
        await self.player.monitor('men_piao_3')
        await asyncio.sleep(1)

    
    async def _do_fight(self, idx):
        self.logger.info('_do_fight')
        pos_fights = [
            (650, 250),
            (650, 330),
            (650, 415),
        ]

        await self.player.click(pos_fights[idx])

        res = await self.player.click_untile_disappear(['fight_green', 'fight_green_1'])
        if not res:
            await self._set_team_offense()
            await self.player.find_then_click(['fight_green', 'fight_green_1'])

        pos_ok = (440, 430)
        while True:
            try:
                name = await self.player.find_then_click(['card', 'ok12', 'ok16', 'next', 'next1', 'go_last'])
            except FindTimeout:
                # 达到战斗上限了
                await self.player.find_then_click(CLOSE_BUTTONS)
                raise PlayException("reach max fight num")

            if name == 'card':
                await self.player.click(pos_ok)
                result = await self.player.find_then_click(['win', 'lose'], threshold=0.9)
                return 2 if result == 'win' else 1

            await asyncio.sleep(1)
