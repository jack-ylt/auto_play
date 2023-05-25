##############################################################################
# 自动完成每日游戏任务，收集资源
#
##############################################################################

import asyncio
import logging
from logging.handlers import RotatingFileHandler
import math
import os
import random
import re
import shutil
import time
from collections import namedtuple
from datetime import datetime
from operator import itemgetter
from pickle import NEXT_BUFFER

from cv2 import threshold


from lib.helper import is_afternoon, is_monday, is_sunday, is_wednesday, format_text
from lib.player import FindTimeout, Player
from lib.ui_data import CLOSE_BUTTONS, GOOD_TASKS, OK_BUTTONS, SCREEN_DICT

# from ui_data import SCREEN_DICT
# from player import Player, FindTimeout


def filter_rightmost(pos_list):
    """get the rightmost position"""
    pos = max(pos_list)
    return pos


def filter_first(pos_list):
    pos = pos_list[0]
    return pos


def filter_top(pos_list):
    lst = sorted(pos_list, key=lambda x: x[1])
    pos = lst[0]
    return pos


def filter_bottom(pos_list):
    lst = sorted(pos_list, key=lambda x: x[1])
    pos = lst[-1]
    return pos


class PlayException(Exception):
    pass


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


class XianShiJie(Task):
    """现世界"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        """验证任务是否已经完成"""
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 3

    async def run(self):
        if not self.test():
            return

        await self._enter()

        await self._collect_box()
        if self._get_count('count') < 3:
            for _ in range(2):
                await asyncio.sleep(10)
                await self._collect_box()
            self._increate_count('count', 3)
        else:
            self._increate_count('count', 1)

        # 现在有自动推图功能了
        while True:
            try:
                await self._goto_next_fight()
            except PlayException:
                await self.player.click(self._back_btn)
                return

            res = await self._fight()
            if res == 'lose':
                await self.player.monitor('ranking_icon')
                await self.player.click(self._back_btn)
                return

    def test(self):
        return self.cfg['XianShiJie']['enable']

    async def _enter(self):
        try:
            await self.player.find_then_click('level_battle', timeout=1)
        except FindTimeout:
            await self._move_to_center()
            await self.player.find_then_click('level_battle')
        await self.player.monitor('ranking_icon')

        # 新号前10天，要领取奖励
        try:
            await self.player.monitor('song_hao_li', timeout=2)
        except FindTimeout:
            return
        else:
            name, pos = await self.player.monitor('ke_ling_qv')
            await self.player.click((pos[0], pos[1] - 50))
            await self.player.find_then_click(OK_BUTTONS)
            try:
                await self.player.find_then_click('close_btn1')
                await asyncio.sleep(1)
                await self.player.find_then_click('close_btn1', timeout=2)
            except FindTimeout:
                pass

    async def _collect_box(self):
        pos_box = (750, 470)
        await self.player.click(pos_box)
        await self.player.find_then_click('receive', raise_exception=False)

    async def _goto_next_fight(self):
        name, pos = await self.player.monitor(['upgraded', 'next_level', 'already_passed', 'fight'])
        if name == 'upgraded':
            await self._hand_upgraded()
            await self._goto_next_fight()
        elif name == 'next_level':
            await self._nextlevel_to_fight(pos)
        elif name == 'already_passed':
            # await self._passed_to_fight()
            raise PlayException("Skip, the user went back to level")
        else:    # fight
            await self.player.click_untile_disappear('fight')

    async def _hand_upgraded(self):
        try:
            await self.player.find_then_click('map_unlocked')
        except FindTimeout:
            return

        await asyncio.sleep(5)
        await self._enter()

    async def _nextlevel_to_fight(self, pos):
        """go from next_level to fight"""
        await self.player.click(pos)
        name, pos = await self.player.monitor(['search', 'fan_hui', 'level_low', 'reach_max_level'])
        if name == 'level_low' or name == 'reach_max_level':
            await self.player.click(pos)
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)
        elif name == 'search':
            await self.player.click(pos)
        else:
            _, pos = await self.player.monitor('fu_biao')
            if pos[0] > 700 and pos[1] < 150:
                # 前往下一个大关卡
                await self._goto_next_map()
            else:
                # 前往下一个小关卡
                await self._goto_next_area()

        await asyncio.sleep(3)
        await self.player.click_untile_disappear(['fight'])

    # TODO: 所有都完成了如何处理？
    async def _goto_next_map(self):
        self.logger.debug('goto next map')
        x_list = [200, 275, 355, 430, 510, 586, 660]
        y = 65
        for x in x_list:
            await self.player.click((x, y))
            await asyncio.sleep(2)
            pos_list = await self.player.find_all_pos(['point', 'point2', 'point3', 'point4'], threshold=0.88)
            # 正常是一个point都没有的，3个是作为buffer
            if len(pos_list) < 3:
                break

        # 每个大关卡的第一个区域坐标
        await self.player.click((200, 250))
        await self.player.find_then_click('ok1')

    async def _goto_next_area(self):
        await asyncio.sleep(5)
        self.logger.debug('goto next area')
        pos_list = await self.player.find_all_pos(['point', 'point2', 'point3', 'point4'], threshold=0.88)
        pos = await self._guess_next_pos(pos_list)
        await self.player.click(pos)
        await self.player.find_then_click('ok1')

    async def _guess_next_pos(self, pos_list):
        pos_list = sorted(pos_list)
        _, (x, y) = await self.player.monitor('fu_biao')

        # 只有最右下角的小地图，才需要往上点，去往下一个小地图
        if 600 < x < 700 and 300 < y < 420:
            new_list = pos_list[-7:]
            pos = sorted(new_list, key=lambda x: x[1])[0]
            return (pos[0], pos[1] - 50)
        else:
            pos = pos_1 = pos_list[-1]
            pos_2 = pos_list[-2]
            if pos_1[1] - pos_2[1] < -15:
                return (pos[0] + 50, pos[1] - 25)
            elif pos_1[1] - pos_2[1] > -15:
                return (pos[0] + 50, pos[1] + 25)
            else:
                return (pos[0] + 50, pos[1])

    async def _passed_to_fight(self):
        """go from already_passed to fight"""
        # TODO next_level2 可能误识别，这样点了就没反应
        await self.player.find_then_click(['next_level2', 'next_level3'], threshold=0.85)

        try:
            name, pos = await self.player.monitor(['search', 'level_low', 'reach_max_level'])
        except FindTimeout:
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)

        if name == 'level_low' or name == 'reach_max_level':
            await self.player.click(pos)
            msg = "Reach the max level, so exit level battle"
            raise PlayException(msg)
        await self.player.click(pos)
        await asyncio.sleep(3)
        await self.player.click_untile_disappear(['fight'])


class YouJian(Task):
    """邮件"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        return True

    def test(self):
        return self.cfg['YouJian']['enable']

    async def run(self):
        if not self.test():
            return

        # 点左下角，避免广告弹出
        await self.player.find_then_click('mail', pos=(45, 340), cheat=False)
        try:
            # 邮件全部删除了，就没有领取按钮
            await self.player.find_then_click(['yi_jian_ling_qv'], timeout=5)
            # 已经领取过了，就不会弹出ok按钮
            await self.player.find_then_click(OK_BUTTONS, timeout=5)
        except FindTimeout:
            pass


class HaoYou(Task):
    """好友"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._fight_boss = self._get_cfg('fight_boss')

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('friends')
        await self.player.monitor('vs')    # 确保完全进入界面
        await self.player.find_then_click('receive_and_send')

        # 刷好友的boos
        if self._fight_boss:
            while True:
                try:
                    await self.player.find_then_click('friend_boss', timeout=1)
                except FindTimeout:
                    break
                if not await self._fight_friend_boss():
                    break

        # 刷自己的boos
        await self.player.find_then_click('friends_help')
        while True:
            if not await self._found_boos():
                break
            if not self._fight_boss:
                break

            await self.player.find_then_click('fight2')
            if not await self._fight_friend_boss():
                break

        self._increate_count('count', 1)

    def test(self):
        return self.cfg['HaoYou']['enable']

    # TODO 有可能好友boos被别人杀掉了
    """重构

    if not  enter fight
        return

    max_try = 2
    count = 0

    while true:
        win = do fight
        count += 1

        if win
            break

        if count >= max_try:
            break

        if not go_next_fight
            break

    click ok and wait hao you lie biao (exit fight)
    
    """

    async def _fight_friend_boss(self):
        try:
            await self.player.find_then_click('fight3')
        except FindTimeout:
            self.logger.debug(f"Skip, reach the fight limit.")
            return False

        try:
            await self.player.find_then_click('start_fight', timeout=3)
        except FindTimeout:
            self.logger.debug(f"Skip, lack of physical strength.")
            return False

        try:
            await self.player.monitor(['empty_box', 'empty_box5'], timeout=1)
            self.logger.debug(f"Skip, user haven't set the fighting team")
            await self.player.find_then_click(CLOSE_BUTTONS)
            return False
        except FindTimeout:
            pass

        max_try = 2
        count = 0

        while True:
            monitor_list = ['card', 'fast_forward1', 'go_last']
            count += 1
            for _ in range(5):
                name, pos = await self.player.monitor(monitor_list, timeout=120)
                if name == "card":
                    await self.player.click_untile_disappear('card')
                    await self.player.click(pos)
                    break
                else:
                    await self.player.click(pos)

            res, pos = await self.player.monitor(['win', 'lose'])
            if res == "win":
                await self.player.find_then_click(OK_BUTTONS)
                return True
            else:
                if count < max_try:
                    try:
                        await self.player.find_then_click('next2')
                    except FindTimeout:
                        self.logger.debug(f"Lose, lack of physical strength.")
                        return False
                else:
                    await self.player.find_then_click(OK_BUTTONS)
                    self.logger.debug(
                        f"Lose, reach the max fight try: {max_try}")
                    return False

    async def _found_boos(self):
        await self.player.monitor('hao_you_zhu_zhan')

        try:
            _, (x, y) = await self.player.monitor('search1', threshold=0.9, timeout=1)
            await self.player.click((x, y + 15))
        except FindTimeout:
            self.logger.debug("Can't search, search time not reached.")
            return False

        name, pos = await self.player.monitor(['fight2', 'ok', 'ok9'])
        if name == "fight2":
            return True
        else:
            await self.player.click(pos)
            return False


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


class TiaoZhanFuben(Task):
    """挑战副本"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 6

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('tiao_zhan_fu_ben')
        await self.player.monitor(CLOSE_BUTTONS)

        for (x, y) in await self.player.find_all_pos('red_point'):
            await self.player.click((x-50, y+20))

            button_name = await self._click_bottom_button()
            if button_name == 'sao_dang':
                await self._sao_dang()
            else:
                await self._tiao_zhan()

            await self.player.find_then_click(CLOSE_BUTTONS)

        await self.player.find_then_click(CLOSE_BUTTONS)

    def test(self):
        return self.cfg['TiaoZhanFuben']['enable'] and self._get_count('count') < 6

    async def _click_bottom_button(self):
        await self.player.monitor(['mop_up', 'mop_up1', 'mop_up2', 'challenge3'])
        await asyncio.sleep(1)    # 等待页面稳定
        sao_dang_list = await self.player.find_all_pos(['mop_up', 'mop_up1', 'mop_up2'])
        tiao_zhan_list = await self.player.find_all_pos('challenge3')
        pos = filter_bottom(tiao_zhan_list + sao_dang_list)

        await self.player.click(pos)

        if pos in sao_dang_list:
            return 'sao_dang'
        return 'tiao_zhan'

    async def _sao_dang(self):
        self._increate_count('count')
        # 有可能本来就只有一场扫荡
        name = await self.player.find_then_click(['next_game1'] + OK_BUTTONS)
        if name == 'next_game1':
            await self.player.find_then_click(OK_BUTTONS)
            self._increate_count('count')

    async def _tiao_zhan(self):
        await self.player.click_untile_disappear('start_fight')
        res = await self._fight_challenge()

        if res == 'win':
            self._increate_count('count')
            name = await self.player.find_then_click(['xia_yi_chang'] + OK_BUTTONS)
            if name == 'xia_yi_chang':
                await self._fight_challenge()
                self._increate_count('count')
        else:
            self.logger.warning("Fight lose in TiaoZhanFuben")

        await self.player.find_then_click(OK_BUTTONS)

    async def _fight_challenge(self):
        for _ in range(24):
            await self.player.find_then_click('go_last')
            try:
                await self.player.monitor('fight_report')
            except FindTimeout:
                continue
            else:
                break
        res, _ = await self.player.monitor(['win', 'lose'])
        return res


class GongHui(Task):
    """公会"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('gong_hui')
        name, _ = await self.player.monitor(['gong_hui_ling_di', 'join_guild'])
        if name == 'join_guild':
            return    # 还没有参加公会，则跳过

        await self._gong_hui_qian_dao()

        # name, pos = await self.player.monitor(['tui_jian_gong_hui', 'gong_hui_ling_di'])
        # if name == 'tui_jian_gong_hui':
        #     return

        await self.player.find_then_click('gong_hui_ling_di')

        if self._get_cfg('fight_boss') and self._get_count('fight_boss') != 0:
            await self._gong_hui_fu_ben()
            await self.player.go_back_to('guild_factory')
            self._increate_count('fight_boss')

        await self._gong_hui_gong_chang()

        self._increate_count('count')

    def test(self):
        return self.cfg['GongHui']['enable']

    async def _gong_hui_qian_dao(self):
        await self.player.monitor('gong_hui_ling_di')
        await self.player.find_then_click('sign_in', threshold=0.95, timeout=1, raise_exception=False)

    async def _gong_hui_fu_ben(self):
        await self.player.find_then_click('gong_hui_fu_ben')
        await self.player.monitor('gong_hui_boos')

        name, pos = await self.player.monitor(['boss_card_up', 'boss_card_down'], threshold=0.92, timeout=3)
        # 匹配的是卡片边缘，而需要点击的是中间位置
        if name == 'boss_card_up':
            pos = (pos[0], pos[1]+50)
        else:
            pos = (pos[0], pos[1]-50)
        await self.player.click(pos)

        await self.player.monitor('ranking_icon2')
        await asyncio.sleep(1)
        if self.player.is_exist(['zuan_shi', 'zuan_shi1']):
            # 避免花费钻石
            return

        try:
            await self.player.find_then_click('fight4', threshold=0.8, timeout=2)
        except FindTimeout:
            return

        # 小号通常不会设置队伍，也最好不要打公会战
        await self.player.monitor(CLOSE_BUTTONS)  # 等待战斗页面出来
        try:
            await self.player.monitor(['empty_box', 'empty_box5'], timeout=1)
            return
        except FindTimeout:
            pass

        await self._fight_guild()

    async def _fight_guild(self):
        # next_fight = (520, 425)

        await self.player.click_untile_disappear('start_fight')
        await self._go_last()

        # await self.player.click(next_fight)
        await self.player.click_untile_disappear('next_fight')
        await self._go_last()

        await self.player.find_then_click('ok')
        await self.player.monitor('ranking_icon2')

    async def _go_last(self):
        # go_last 按钮有时候会被boos挡住，所以没用find_then_click
        await self.player.monitor(['message', 'go_last'])
        await asyncio.sleep(2)

        pos_go_last = (835, 56)
        for i in range(3):
            await self.player.click(pos_go_last, cheat=False)
            try:
                await self.player.monitor('fight_report', timeout=2)
                return
            except FindTimeout:
                self.logger.warning(f"try {i}, go_last failed.")
                pass

        await self.player.monitor('fight_report', timeout=240)

    async def _gong_hui_gong_chang(self):
        await self.player.find_then_click('guild_factory')

        try:
            for _ in range(2):
                await self.player.find_then_click(['order_completed', 'ok1'], timeout=3)
        except FindTimeout:
            pass

        await self.player.find_then_click('get_order')
        try:
            await self.player.monitor('start_order', timeout=1)
        except FindTimeout:
            pass
        else:
            await self.player.find_then_click('yi_jian_kai_shi_ding_dan')

        await self.player.find_then_click('donate_home')
        await self.player.find_then_click(self.cfg['GongHui']['donate'])
        try:
            await self.player.find_then_click(['ok5'], timeout=2)
        except FindTimeout:
            pass


class MeiRiQianDao(Task):
    """每日签到"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('jing_cai_huo_dong')
        for _ in range(3):
            await self.player.find_then_click('qian_dao')

        self._increate_count('count', 1)

        # 领取周礼包、月礼包
        for pos in await self.player.find_all_pos('red_point2'):
            await self.player.click((pos[0] - 80, pos[1] + 30))
            await self.player.monitor('mian_fei')
            await self.player.click((405, 250))
            await self.player.find_then_click('5_xing_sui_pian')
            await self.player.find_then_click('ok_btn2')
            await self.player.find_then_click('mian_fei')
            await self.player.find_then_click(OK_BUTTONS)

    def test(self):
        return self.cfg['MeiRiQianDao']['enable']


class JueDiKongJian(Task):
    """绝地空间"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self.camp_dict = {
            'xie_e': 0,
            'shou_hu': 1,
            'hun_dun': 2,
            'zhi_xu': 3,
            'chuang_zao': 4,
            'hui_mie': 5,
        }

    def verify(self):
        if not self._get_cfg('enable'):
            return True
        return self._get_count('count') >= 1

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_top()
        await self.player.find_then_click('jedi_space')

        # 要80即才解锁
        try:
            await self.player.monitor('challenge5')
        except FindTimeout:
            self._increate_count()    # 用于verify, 表示完成了
            return

        await self._choose_camp()
        await self.player.find_then_click('challenge5')

        await self.player.monitor('ying_xiong_lie_biao')
        try:
            # 一关都没通过，就没有扫荡
            await self.player.find_then_click('mop_up3', timeout=2)
            # 扫荡完了，就不会弹出扫荡窗口
            await self.player.find_then_click(['max'], timeout=3, cheat=False)
            self._increate_count()
        except FindTimeout:
            return

        await self.player.find_then_click(OK_BUTTONS)

    def test(self):
        return self._get_cfg('enable') and self._get_count('count') < 1

    async def _choose_camp(self):
        left = (90, 240)
        right = (780, 240)

        num = self.camp_dict[self.cfg['JueDiKongJian']['camp']]

        if num == 0:
            return
        elif num <= 3:
            pos_button = left
        else:
            pos_button = right
            num = 6 - num

        for _ in range(num):
            await self.player.click(pos_button, cheat=False)
            await asyncio.sleep(0.5)


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

        await self.player.find_then_click('fight_btn')

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


class YaoQingYingXion(Task):
    """邀请英雄"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_down()
        await self.player.find_then_click('invite_hero')
        await self.player.monitor('beer')
        pos_list = await self.player.find_all_pos(['invite_free', 'invite_soda', 'invite_beer'])

        for p in pos_list:
            if p[0] > 300:    # 是右边的高级邀请按钮
                self._increate_count('count_gao_ji_yao_qing')
            else:
                self._increate_count('count_pu_tong_yao_qing')

            await self.player.click(p)
            name, _ = await self.player.monitor(['ok9', 'ok10', 'ok17', 'close'])
            # 如果英雄列表满了，就遣散英雄
            if name == 'close':
                self.logger.warning(
                    "The hero list is full, so need dismiss heroes")
                pos_list.append(p)    # 没邀请成功，就再试一次
                await self.player.find_then_click('qian_san_btn')
                await self._dismiss_heroes()
            else:
                await self.player.find_then_click(name)    # 要避免点太快

        # 购买光暗3星
        if self._get_count('mai_guang_an_3_xing') > 0:
            return
        
        await self.player.find_then_click('pi_jiu_icon')
        await self.player.monitor('pi_jiu_icon1')
        await self._swipe_left()

        for _ in range(2):
            try:
                _, pos = await self.player.monitor(['guang_san_xing', 'an_san_xing'], threshold=0.9, timeout=2)
                await self.player.click((pos[0], pos[1] + 80))
            except FindTimeout:
                break
            await self.player.find_then_click('max2')
            await self.player.find_then_click('gou_mai')
            await self.player.find_then_click(OK_BUTTONS)
        
            self._increate_count('mai_guang_an_3_xing', validity_period=7)
        


    def test(self):
        if not self.cfg['YaoQingYingXion']['enable']:
            return False
        if self._get_count('count_gao_ji_yao_qing') >= 1:
            return False
        return True

    async def _dismiss_heroes(self):
        await self.player.find_then_click('1xing')
        await self.player.find_then_click('quick_put_in')
        await self.player.find_then_click('2xing')
        await self.player.find_then_click('quick_put_in')

        # 如果遣散栏为空，就遣散3星英雄
        try:
            await self.player.monitor('empty_dismiss', timeout=1)
        except FindTimeout:
            await self.player.find_then_click('dismiss')
            await self.player.find_then_click('receive1')
        else:
            await self.player.find_then_click('3xing')
            await self.player.find_then_click('quick_put_in')
            await self.player.find_then_click('dismiss')
            await self.player.find_then_click(OK_BUTTONS)
            await self.player.find_then_click('receive1')

        # 回到啤酒邀请界面
        await self.player.go_back()


    async def _swipe_left(self):
        p1 = (650, 275)
        p2 = (250, 275)
        await self.player.drag(p1, p2, stop=True)

class WuQiKu(Task):
    """武器库"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()

    async def run(self):
        if not self.test():
            return

        num_list = ['num_0', 'num_1', 'num_2', 'num_3']
        pos_quantity = (220, 330)
        pos_enter = (810, 480)
        pos_forging = (250, 450)

        await self._move_to_right_top()
        await self.player.find_then_click('armory')
        await self.player.monitor('armory_list')

        count = 0
        max_num = 3    # 每日任务要求锻造3次
        while True:
            pos = self._select_equipment_randomly()
            if not pos:
                break
            await self.player.click(pos)
            await self.player.information_input(pos_quantity, str(max_num - count))
            await self.player.click(pos_enter)
            name, _ = await self.player.monitor(num_list, threshold=0.9)
            count += num_list.index(name)
            await self.player.click(pos_forging)
            # 如果锻造数量是0的话，不会弹出对话框
            await self.player.find_then_click(OK_BUTTONS, timeout=3, raise_exception=False)

            if count >= 3:
                self._increate_count('count', 3)
                return

        self.logger.warning("There are not enough equipment for synthesis.")

    def test(self):
        return self.cfg['WuQiKu']['enable'] and self._get_count('count') < 3

    def _select_equipment_randomly(self):
        """随机选择锻造装备，不能每次都薅同一只羊"""
        pos_types = [
            (820, 190),
            (820, 270),
            (820, 350),
            (820, 440),
        ]

        while True:
            if len(self._seen) == len(pos_types):
                return ()
            pos = random.choice(pos_types)
            if pos not in self._seen:
                self._seen.add(pos)
                return pos


class XingCunJiangLi(Task):
    """幸存奖励

    一天领一次就可以了，以便于一次性完成所有日常任务
    """

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()

    async def run(self):
        if not self.test():
            return

        pos_plus = (412, 54)
        pos_receive = (350, 390)

        await self.player.click(pos_plus, cheat=False)
        await self.player.monitor('xing_cun_jiang_li')
        for _ in range(2 - self._get_count()):
            await self.player.click(pos_receive)
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=2)
                self._increate_count()
            except FindTimeout:
                break

    def test(self):
        return self._get_cfg('enable') and self._get_count() < 2


class ShiChang(Task):
    """市场"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_down()
        await self.player.find_then_click('market')
        await self.player.monitor(['gold', 'diamond'])

        for _ in range(4):
            await self._buy_goods()
            if not await self._refresh_new_goods():
                break

        # 高级市场
        if self._get_count() < 1:
            self._increate_count()

            await self.player.find_then_click('gao_ji')
            try:
                await self.player.monitor('gold_30m')
            except FindTimeout:
                # 100级以上才解锁
                return

            if self._get_cfg('mai_lv_yao'):
                await self.player.find_then_click('gold_30m')
                try:
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                except FindTimeout:
                    # 如果金币不足，忽略
                    pass

            if self._get_cfg('mai_men_piao'):
                await self.player.find_then_click('xia_yi_ye')
                await self.player.find_then_click('gold_300k')
                try:
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                except FindTimeout:
                    # 如果金币不足，忽略
                    pass

            goods_list = []
            if self._get_cfg('mai_bao_tu'):
                goods_list.append('bao_tu')

            if self._get_cfg('mai_pi_jiu'):
                goods_list.append('pi_jiu1')

            if self._get_cfg('mai_hui_zhang'):
                goods_list.append('hui_zhang1')

            if goods_list:
                await self.player.find_then_click('xia_yi_ye', timeout=1, raise_exception=False)
                for goods in goods_list:
                    _, pos = await self.player.monitor(goods)
                    await self.player.click((pos[0], pos[1] + 70))
                    try:
                        await self.player.find_then_click(OK_BUTTONS)
                        await self.player.find_then_click(OK_BUTTONS)
                    except FindTimeout:
                        # 如果钻石不足，直接结束
                        self.logger.warning("钻石不足")
                        return

    def test(self):
        return self.cfg['ShiChang']['enable']

    async def _buy_goods(self):
        nice_goods = ['task_ticket', 'hero_badge', 'arena_tickets',
                      'soda_water', 'hero_blue', 'hero_green',
                      'hero_light_blue', 'hero_red', 'bao_shi',
                      'xing_pian_bao_xiang']
        list1 = await self.player.find_all_pos('gold')
        list2 = await self.player.find_all_pos(nice_goods)
        pos_list1 = self._merge_pos_list(list1, list2, dx=50, dy=100)

        list3 = await self.player.find_all_pos('diamond_1000')
        list4 = await self.player.find_all_pos('beer_8')
        pos_list2 = self._merge_pos_list(list3, list4, dx=50, dy=100)

        for pos in sorted(pos_list1 + pos_list2):
            if await self.player.is_disabled_button(pos):
                continue
            await self.player.click((pos[0] + 30, pos[1]))
            try:
                name, pos = await self.player.monitor(['lack_of_diamond', 'ok8'], timeout=3)
            except FindTimeout:
                # 金币不足，或者点击没反应
                continue
            else:
                if name == 'ok8':
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.find_then_click(OK_BUTTONS)
                else:
                    await self.player.find_then_click(CLOSE_BUTTONS)

    async def _refresh_new_goods(self):
        fresh_btn = (690, 135)
        await self.player.click(fresh_btn)
        try:
            await self.player.find_then_click('cancle', timeout=2)
            return False
        except FindTimeout:
            return True


class JingJiChang(Task):
    """竞技场"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._seen = set()
        self.num = int(self._get_cfg('fight_num'))
        self.count = self._get_count('count')

    async def run(self):
        if not self.test():
            return

        await self._move_to_left_top()
        await self.player.find_then_click('arena')
        await self.player.find_then_click('enter')

        if is_afternoon:
            c = self.count
            if is_monday() and self.num >= 7:
                num = self.num + 1 - c     # 确保一周战斗50次
            else:
                num = self.num - c
        else:
            num = min(3, self.num - self.count)

        win, lose = 0, 0
        page = 0
        for i in range(num):
            try:
                page = await self._choose_opponent(page)
            except PlayException:
                return

            if await self._fight_win():
                win += 1
            else:
                lose += 1
                page += 1

        self.logger.debug(
            f"JingJiChang: win: {win}, lose: {lose}, page: {page}")
        self._increate_count('count', num)

        await self._collect_award()

    def test(self):
        if not self.cfg['JingJiChang']['enable']:
            return False
        if self.count >= self.num:
            return False
        if (not is_afternoon()) and self.count >= 3:
            return False
        return True

    async def _choose_opponent(self, page=0):
        # 避免速度太快，把确定误识别战斗
        await self.player.monitor('fight_ico')
        await self.player.find_then_click('fight7')

        # 经常 monitor fight8 超时，所以多试一次
        await asyncio.sleep(2)
        await self.player.find_then_click('fight7', timeout=1, raise_exception=False)

        for _ in range(page):
            self.player.find_then_click('refresh5')

        for _ in range(2):
            await self.player.monitor('fight8')
            pos_list = await self.player.find_all_pos('fight8')
            await self.player.click(filter_bottom(pos_list))
            name, _ = await self.player.monitor(['buy_ticket', 'start_fight'])

            if name == 'start_fight':
                await self.player.click_untile_disappear('start_fight')
            else:
                raise PlayException('lack of ticket.')

            await asyncio.sleep(3)    # 避免速度太快
            try:
                # 同一个人不能打太多次
                # 结算前5分钟不能战斗
                # TODO 这种情况，不要_verify_monitor，就可以准确判断是那种情况了
                await self.player.monitor('close8', timeout=1)
            except FindTimeout:
                return page
            else:
                await self.player.find_then_click('close8')
                await self.player.find_then_click('refresh5')
                page += 1

        # 如果两次都无法进入战斗，可能是在结算期了
        raise PlayException('_choose_opponent failed')

    async def _fight_win(self):
        name_list = ['card', 'fast_forward1', 'go_last']
        while True:
            name, pos = await self.player.monitor(name_list, threshold=0.9, timeout=10)
            if name == 'card':
                await self.player.click_untile_disappear('card')
                await self.player.click(pos)
                break
            else:
                await self.player.click(pos)
            await asyncio.sleep(1)

        res, _ = await self.player.monitor(['win', 'lose'])
        await self.player.find_then_click(OK_BUTTONS)
        return res

    async def _collect_award(self):
        await self.player.find_then_click('award')
        await self.player.monitor('receive_list')
        while True:
            pos_list = await self.player.find_all_pos('receive2')
            if not pos_list:
                break
            await self.player.click(filter_top(pos_list))
            try:
                await self.player.find_then_click(OK_BUTTONS, timeout=2)
            except FindTimeout:
                break


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
                if zhan_li > await self._get_self_power():
                    continue

                # 如果积分太低，后面的人只会更低 (不一定)
                # 没到钻石之前，要打积分够多的人，节约门票
                if not self.is_zuanshi:
                    if zhan_li in self.too_poor:
                        continue
                    ji_fen_enemy = await self._get_enemy_score(j)
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
            (430, 245, 490, 280),
            (430, 327, 490, 362),
            (430, 409, 490, 444),
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


class YongZheFuBen(Task):
    """勇者副本"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._enter()

        for i in range(15):
            try:
                await self._goto_fight()
            except FindTimeout:
                self.logger.debug('goto fight failed, check if finished.')
                if await self._finished():
                    return

            # 每一期, 第一次进入可能都要重新设置阵容
            if i == 0:
                await self._equip_team()
                try:
                    await self.player.monitor('lack_of_hero', timeout=1)
                    self.logger.debug('skip, lack 0f heroes.')
                    return
                except FindTimeout:
                    pass

            if not await self._fight_win():
                await self.player.find_then_click(OK_BUTTONS)
                return

    def test(self):
        return self.cfg['YongZheFuBen']['enable']

    async def _enter(self):
        await self._move_to_right_top()
        await self.player.find_then_click('brave_instance')
        await self.player.monitor('brave_coin')

    async def _goto_fight(self):
        # current_level: 第一次进入
        # ok：非第一次，非vip
        # next_level4：非第一次，vip
        name, pos = await self.player.monitor(['huo_de_wu_ping', 'next_level4', 'ok', 'current_level'], timeout=2, verify=False)
        if name == 'huo_de_wu_ping':
            await self.player.find_then_click(OK_BUTTONS)
            name, pos = await self.player.monitor(['next_level4', 'ok', 'current_level'], timeout=2, verify=False)

        if name == 'next_level4':
            await self.player.click(pos)
            await self.player.find_then_click('challenge4')
            return True
        elif name == 'ok':
            await self.player.click(pos)
            await self.player.monitor('brave_coin')

        try:
            # 获得物品可能会这时候弹出来
            await self.player.monitor('huo_de_wu_ping', timeout=2)
            await self.player.find_then_click(OK_BUTTONS)
        except FindTimeout:
            pass

        _, (x, y) = await self.player.monitor('current_level', threshold=0.95, timeout=5)
        await self.player.click((x, y + 35), cheat=False)
        await self.player.find_then_click('challenge4')

    async def _fight_win(self):
        # await self.player.find_then_click('start_fight')
        await self.player.click_untile_disappear('start_fight')

        # 5次不一定够用，因为不要60级，无法go_last
        # for _ in range(5):
        while True:
            # 10s 有时候会timeout
            name, pos = await self.player.monitor(['card', 'lose', 'win', 'go_last', 'fast_forward1', 'huo_de_wu_ping'], timeout=20)
            if name == "card":
                await self.player.click_untile_disappear('card')
                await self.player.click(pos)
                return True
            elif name == 'win':
                return True
            elif name == 'huo_de_wu_ping':
                await self.player.find_then_click(OK_BUTTONS)
            elif name in ['go_last', 'fast_forward1']:
                await self.player.click(pos)
            else:
                return False
            await asyncio.sleep(1)

    async def _finished(self):
        await self.player.monitor('brave_coin')
        try:
            await self.player.monitor('brave_finished', timeout=1)
            self.logger.debug('YongZheFuBen is finished.')
            return True
        except FindTimeout:
            return False


class XingYunZhuanPan(Task):
    """幸运转盘"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._move_to_right_top()
        await self.player.find_then_click('lucky_draw')
        await self.player.find_then_click('draw_once')
        await asyncio.sleep(8)
        await self.player.find_then_click('draw_again')

        self._increate_count('count', 2)

    def test(self):
        if not self.cfg['XingYunZhuanPan']['enable']:
            return False
        if self._get_count('count') >= 2:
            return False
        return True


class RenWuLan(Task):
    """任务栏"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._good_tasks = [
            'task_3star',
            'task_4star',
            'task_5star',
            'task_6star',
            'task_7star'
        ]
        self._tasks_to_finish = [
            'task_3star',
            'task_4star',
            'task_5star',
        ]

    async def run(self):
        if not self.test():
            return

        await self._enter()

        try:
            await self.player.monitor('receivable_task', timeout=1)
        except FindTimeout:
            self.logger.info("Skip, there is no receivable task")
            return

        await self._accept_all_tasks()
        await self._finish_all_tasks()
        await self._refresh_tasks()
        await self._accept_and_finish_left_tasks()

        self._increate_count('count')

    def test(self):
        # return self.cfg['RenWuLan']['enable'] and self._get_count('count') < 1
        return True

    async def _enter(self):
        try:
            await self.player.monitor('task_board', timeout=1)
        except FindTimeout:
            await self._move_to_center()
        await self.player.find_then_click('task_board')
        await self.player.monitor(['unlock', 'lock'])

    async def _accept_all_tasks(self):
        for _ in range(5):
            await self._accept_tasks()
            await self._swip_to_right()

            try:
                await self.player.monitor('receivable_task', timeout=1, verify=False)
            except FindTimeout:
                return

            try:
                await self.player.monitor(['finish_btn', 'unlock_more'], timeout=1)
                break
            except FindTimeout:
                pass

            # 避免到主界面，还在死循环
            try:
                await self.player.monitor(['unlock', 'lock'], timeout=1)
            except FindTimeout:
                break

        # 到了右边，但可能还有receivable_task
        await self._accept_tasks()

    async def _accept_tasks(self):
        list1 = await self.player.find_all_pos('receivable_task')
        list2 = await self.player.find_all_pos(self._good_tasks, threshold=0.85)
        pos_list = self._merge_pos_list(list1, list2, dx=10)
        for pos in pos_list:
            await self.player.monitor('receivable_task')
            await self.player.click(pos)
            await self.player.find_then_click('yi_jian_shang_zhen')
            await self.player.find_then_click('kai_shi_ren_wu')

            # 注意：有可能英雄不够，则需要关闭窗口，继续往下运行
            try:
                await self.player.find_then_click(CLOSE_BUTTONS, timeout=1)
                print("英雄不够")
                return False
            except FindTimeout:
                pass
        return True

    async def _swip_to_right(self, stop=True):
        pos_r = (800, 300)
        pos_l = (10, 300)
        await self.player.drag(pos_r, pos_l, speed=0.02, stop=stop)

    async def _refresh_tasks(self):
        if self._get_count('refresh_num') >= int(self._get_cfg('refresh_num')):
            return False
        await self.player.find_then_click('refresh4')
        await asyncio.sleep(2)
        try:
            await self.player.monitor('lack_of_diamond', timeout=1)
        except FindTimeout:
            self._increate_count('refresh_num')
            return True
        else:
            await self.player.find_then_click(CLOSE_BUTTONS)
            return False

    async def _finish_all_tasks(self):
        # vip finish
        await self.player.find_then_click('one_click_collection2')
        try:
            await self.player.find_then_click(OK_BUTTONS, timeout=2)
            await asyncio.sleep(2)
            await self.player.find_then_click(OK_BUTTONS)
            self.logger.info("All tasks had been finished.")
            return
        except FindTimeout:
            pass

        # 非vip也只领取5星及以下的任务（保持一致性）
        for _ in range(5):
            list1 = await self.player.find_all_pos('finish_btn')
            list2 = await self.player.find_all_pos(self._tasks_to_finish)
            pos_list = self._merge_pos_list(list1, list2, dx=10)
            if pos_list:
                await self.player.click(sorted(pos_list)[0])
                await self.player.find_then_click(OK_BUTTONS)
                # 5星以上任务，会有两个ok确认
                await self.player.find_then_click(OK_BUTTONS, timeout=2, raise_exception=False)
            else:
                try:
                    await self.player.monitor('unlock_more', timeout=1)
                    break
                except FindTimeout:
                    await self._swip_to_right()

            # 避免到主界面，还在死循环
            try:
                await self.player.monitor(['unlock', 'lock'], timeout=1)
            except FindTimeout:
                break

    async def _accept_and_finish_left_tasks(self):
        """完成1星、2星任务

        以便一次性完成所有日常任务
        """
        for _ in range(10):
            try:
                await self.player.find_then_click('receivable_task', timeout=2)
                await self.player.find_then_click('yi_jian_shang_zhen')
                await self.player.find_then_click('kai_shi_ren_wu')
            except FindTimeout:
                break

            try:
                await self.player.find_then_click('diamond_0', timeout=2)
                await self.player.find_then_click(OK_BUTTONS)
            except FindTimeout:
                pass


class RenWuLan300(RenWuLan):
    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._good_tasks = [
            'zuan_shi_4xing',
            'pi_jiu_4xing',
            'task_5star',
            'task_6star',
            'task_7star'
        ]
    
    async def run(self):
        await self._enter()
        await asyncio.sleep(3)
        await self._accept_all_tasks()

        if not await self._refresh_tasks():
            return

        end = False
        total_cost = 0
        max_num = 4
        while not end:
            task_num = len(await self.player.find_all_pos('receivable_task'))

            if task_num >= 3:
                # refresh tasks
                if not await self._refresh_tasks():
                    end = True
            else:
                # add tasks
                add_num = max_num - task_num
                total_cost += add_num
                await self._add_task(add_num)

            if self.player.is_exist('task_7star'):
                print("刷到了7星任务")
                end = True

            if not self.player.is_exist('receivable_task'):
                print("没有白信封了")
                end = True

            # accept tasks
            if not await self._accept_tasks():
                end = True
        
        print(f"总共消耗白信封：{total_cost}")

    async def _add_task(self, num):
        for _ in range(num):
            await self.player.click((290, 475))
        await asyncio.sleep(3)

    async def _refresh_tasks(self):
        await self.player.find_then_click('refresh4')
        await asyncio.sleep(2)
        try:
            await self.player.find_then_click(CLOSE_BUTTONS, timeout=2)
            print("钻石不够，无法刷新任务")
            return False
        except FindTimeout:
            return True

class VipShangDian(Task):
    """VIP商店"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        pos_vip = (28, 135)
        await self.player.click(pos_vip, cheat=False)
        await self.player.monitor(['vip_shop', 'vip_shop1'])
        try:
            await self.player.find_then_click('receive_small', timeout=1)
        except FindTimeout:
            pass
        self._increate_count('count')

    def test(self):
        return self.cfg['VipShangDian']['enable'] and self._get_count('count') < 1


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
        text = self.player.get_text((390, 38, 470, 70))
        num = int(text.split('/')[0])
        if num <= 9:
            return 
        
        await self.player.find_then_click('sao_dang')
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
        await self.player.find_then_click('red_point3')
        

    async def _exit(self):
        while True:
            name, pos = await self.player.monitor(['go_back', 'go_back1', 'go_back2', 'setting'])
            if name in ['go_back', 'go_back1', 'go_back2']:
                await self.player.click(pos)
            else:
                break


class RenWu(Task):
    """任务"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('task')
        await self.player.find_then_click('receive_all')

        try:
            await self.player.monitor('qian_wang', threshold=0.9, timeout=1)
        except FindTimeout:
            self._increate_count('count')

    def test(self):
        return self.cfg['RenWu']['enable'] and self._get_count() < 1


class MiGong(Task):
    """迷宫"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        self._increate_count('count')
        try:
            await self.player.find_then_click('maze4', timeout=2, cheat=False)
        except FindTimeout:
            self.logger.debug("There is no maze")
            return

        await self.player.monitor('maze_text')
        await self.player.find_then_click('maze_daily_gift')

        try:
            _, pos = await self.player.monitor('red_point1', timeout=1)
        except FindTimeout:
            self.logger.debug("maze daily gift have been already recived.")
            return

        await self.player.click((pos[0] - 60, pos[1] + 20))

    def test(self):
        return self.cfg['MiGong']['enable'] and self._get_count('count') < 1


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


class KuaiJieZhiNan(Task):
    """快捷每日任务"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click(['quick_ico', 'quick_ico1'])
        await self.player.find_then_click('yi_jian_zhi_xing')
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
            self._increate_count()

    def test(self):
        return self._get_cfg()

    async def _update_counter(self):
        self._increate_count('count', val=3, cls_name='XianShiJie')
        self._increate_count('count', val=2, cls_name='XingYunZhuanPan')
        self._increate_count('count', val=6, cls_name='TiaoZhanFuben')
        self._increate_count('count', val=3, cls_name='WuQiKu')
        self._increate_count('count', val=3, cls_name='JingJiChang')
        self._increate_count('count', val=2, cls_name='XingCunJiangLi')


class LianSaiBaoXiang(Task):
    """收集联赛宝箱"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        try:
            await self.player.find_then_click('lian_sai_bao_xiang', timeout=3)
        except FindTimeout:
            return

        await self.player.find_then_click('lian_sai_bao_xiang_l')
        await self.player.find_then_click(OK_BUTTONS)
        await self.player.go_back()
        self._increate_count()

    def test(self):
        return self._get_cfg('enable') and self._get_count('count') < 1


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


class JiYiDangAnGuan(Task):
    """记忆档案馆"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._move_to_right_top()
        await self.player.find_then_click('ji_yi_dang_an_guan')
        await self.player.monitor('wen_hao')

        try:
            await self.player.find_then_click('yi_jian_ling_qv1', timeout=2)
            await self.player.find_then_click('receive4')
        except FindTimeout:
            pass
        else:
            self._increate_count()

    def test(self):
        return self._get_cfg('enable')


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
            pos_list = self._merge_pos_list(list1, list2, dy=30)

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
                    name, _ = await self.player.monitor(['lack_of_diamond', 'ok8'], timeout=3)
                    if name == 'ok8':
                        await self.player.find_then_click(OK_BUTTONS)
                        await self.player.find_then_click(OK_BUTTONS)
                        continue
                    else:
                        lack_diamond = True

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


# 特殊类，专门用于给小号领取工会boos的箱子
# 用测试模式调用一次就好了
class GongHuiFuBen(Task):
    """公会副本批量开宝箱"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('gong_hui')
        name, _ = await self.player.monitor(['gong_hui_ling_di', 'join_guild'])
        if name == 'join_guild':
            return    # 还没有参加公会，则跳过

        await self.player.find_then_click('gong_hui_ling_di')
        await self.player.find_then_click('gong_hui_fu_ben')

        while True:
            await self.player.monitor('gong_hui_boos')
            if self.player.is_exist('gong_hui_box'):
                await self._collect_box()
            else:
                if self.player.is_exist('1-1', threshold=0.9):
                    break
                await self.player.find_then_click('left_btn')

    def test(self):
        return True

    async def _collect_box(self):
        await self.player.find_then_click('gong_hui_box')
        # await self.player.find_then_click('jiang_li')
        await self.player.monitor('gong_hui_boos_jiang_li')

        for i in range(4):
            if self.player.is_exist('gong_hui_card'):
                await self.player.find_then_click('gong_hui_card')
                break
            else:
                await self.player.find_then_click('right_btn')

        await self.player.find_then_click(CLOSE_BUTTONS)
        # await self.player.go_back()


class JueDiQiuSheng(Task):
    """绝地求生"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self.player.find_then_click('yue_du_huo_dong')
        await self.player.find_then_click('jue_di_qiu_sheng')

        y = 400
        for x in (390, 540, 690):
            for i in range(20):
                await self.player.monitor('hui_zhang2')
                await self.player.click((x, y))    # click fight btn
                await self.player.monitor('sao_dang2')
                # 1 票打不死，就停止
                if self.player.is_exist('bai_fen_bai', threshold=0.9):
                    await self.player.find_then_click('sao_dang2')
                    await self.player.find_then_click(OK_BUTTONS)
                    await self.player.click_untile_disappear('start_fight')
                    await self.player.monitor('huo_de_wu_ping')
                    await self.player.find_then_click(OK_BUTTONS)
                else:
                    await self.player.find_then_click(CLOSE_BUTTONS)
                    break
        
        self._increate_count(validity_period=15)

    def test(self):
        return self._get_cfg('enable') and self._get_count() < 1


class ShiJieBoss(Task):
    """世界Boss"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        # 简单起见，小号不打这个世界Boos了
        try:
            # 可能是跨服联赛，没有boos可以打
            await self.player.find_then_click('shi_jie_boos')
            await self.player.find_then_click('gong_ji', timeout=3)
        except FindTimeout:
            return 
        await self.player.click_untile_disappear('start_fight')

        for i in range(10):
            await self.player.find_then_click('xia_yi_chang')
            await asyncio.sleep(3)

        await self.player.find_then_click(OK_BUTTONS)
        self._increate_count()

    def test(self):
        if self._get_cfg('enable') and datetime.now().weekday() in [0, 1] and self._get_count() < 1:
            return True
        return False



class GaoTaShiLian(Task):
    """高塔试炼"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)

    async def run(self):
        if not self.test():
            return

        await self._enter()

        await self._do_fight()
        
        if self._get_count('fight_count') >= 50:
            self._shi_lian_bao_zang()
            await self.player.go_back_to('gao_ta_te_quan')
            self._shi_lian_shang_dian()

            self._increate_count(validity_period=15)
        
    def test(self):
        return self._get_cfg('enable') and self._get_count() < 1

    async def _enter(self):
        await self._move_to_right_top()
        await self.player.find_then_click('yong_shi_zhi_ta')
        await self.player.find_then_click('gao_ta_shi_lian')
        try:
            await self.player.monitor('gao_ta_te_quan')
            return True
        except FindTimeout:
            return False

    async def _do_fight(self):  
        for _ in range(10):
            await self.player.find_then_click(CLOSE_BUTTONS, raise_exception=False, timeout=3)
            await self.player.find_then_click('0_9', raise_exception=False, timeout=3)
            
            for _ in range(3):
                await self.player.find_then_click('tiao_zhan2')
                try:
                    await self.player.monitor('start_fight', timeout=3)
                except FindTimeout:
                    # 没票了
                    return

                await self._re_equip_team()

                await self.player.find_then_click('start_fight')
                res, _ = await self.player.monitor(['win', 'lose'])
                await self.player.find_then_click(OK_BUTTONS)
                self._increate_count('fight_count', validity_period=15)
                if res != "win":
                    break
    
    async def _re_equip_team(self):
        x_list = [180, 250, 370, 430, 500, 570]
        y = 230
        pos_list = [(x_list[c], y) for c in range(6)]

        await self.player.multi_click(pos_list)
        await self.player.find_then_click('yi_jian_shang_zhen1')
        
    async def _shi_lian_bao_zang(self):
        await self.player.find_then_click('gao_ta_te_quan')
        await self.player.monitor('bao_zang')
        await asyncio.sleep(1)
        await self.player.click((560, 310))
        
    async def _shi_lian_shang_dian(self):
        await self.player.find_then_click('shi_lian_hei_jin')
        await self.player.find_then_click('450')
        await self.player.find_then_click('max3')
        await self.player.find_then_click('gou_mai')
        await self.player.find_then_click(OK_BUTTONS)