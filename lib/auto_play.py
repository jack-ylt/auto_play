from hashlib import blake2b
import time
import os
import asyncio
import shutil
from datetime import datetime
import re
import random
import math
from operator import itemgetter
from collections import namedtuple
from cv2 import threshold
from playsound import playsound
import math

from lib.ui_data import SCREEN_DICT, OK_BUTTONS, GOOD_TASKS, CLOSE_BUTTONS
from lib.player import Player, FindTimeout, GameNotResponding
from lib import tasks

# from ui_data import SCREEN_DICT
# from player import Player, FindTimeout

import logging
logger = logging.getLogger(__name__)


def filter_rightmost(pos_list):
    """get the rightmost position"""
    pos = max(pos_list)
    return pos


def filter_first(pos_list):
    pos = pos_list[0]
    return pos


def filter_bottom(pos_list):
    lst = sorted(pos_list, key=lambda x: x[1])
    pos = lst[-1]
    return pos


def save_timeout_pic(msg):
    # f"{self.window_name}: monitor {names} timeout. ({timeout} s)"
    screen_pic = SCREEN_DICT['screen']
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    window_name = re.search(r'(\w+):', msg).group(1)
    monitor_items = re.search(r'\[.+\]', msg).group()
    # log_pic = os.path.join(
    #     './timeout_pics', f"{timestr}_{window_name}_{monitor_items}.jpg")
    log_pic = os.path.join(
        'logs', window_name, f"{timestr}_{monitor_items}.jpg"
    )
    shutil.copyfile(screen_pic, log_pic)
    logger.info(f"save_timeout_pic: {monitor_items}")
    playsound('./sounds/error.mp3')


class PlayException(Exception):
    pass


class AutoPlay(object):
    def __init__(self, player):
        self.player = player
        self.logger = self.player.logger

 

    async def _close_ad(self, timeout=2):
        try:
            _, pos = await self.player.monitor(['close_btn1', 'close_btn2', 'close_btn3'], timeout=timeout)
            await self.player.click(pos)
        except FindTimeout:
            pass


    def save_operation_pics(self, msg):
        self.player.save_operation_pics(msg)

    async def goto_main_interface(self):
        """通过esc回主界面

        如果esc不行，则业务要自己回主界面
        """
        for i in range(5):
            try:
                await self.player.monitor(['close_btn4', 'setting'], timeout=1)
            except FindTimeout:
                await self.player.go_back()    # ESC 可能失效 (游戏未响应)
            else:
                break

        await self.player.find_then_click(CLOSE_BUTTONS, timeout=1, raise_exception=False)

        try:
            await self.player.monitor('setting', timeout=1)
        except FindTimeout:
            raise PlayException("go to main interface failed")

        return

    async def shen_yuan_mo_ku(self):
        await self._move_to_right_down()
        await self.player.click((635, 350))

        pos_enter = (550, 435)
        while True:
            try:
                await self.player.monitor('ranking_icon4')
                await self.player.click(pos_enter)
                await self.player.find_then_click('skill_preview_btn', timeout=3)
            except FindTimeout as e:
                logger.info("The shen yuan mo ku is not open yet.")
                return False

            if await self.have_good_skills():
                return True

            pos_list = await self.player.find_all_pos(CLOSE_BUTTONS)
            await self.player.click(sorted(pos_list)[0])
            await self.player.find_then_click(CLOSE_BUTTONS)

            # TODO 可能不需要重新登陆
            # await self.re_login()
            # await

    async def have_good_skills(self):
        await self.player.monitor('skill_preview_list')

        try:
            _, pos = await self.player.monitor('you_she_you_de', timeout=1)
        except FindTimeout:
            return False

        if pos[1] < 360:    # 不是在前三个
            return False

        return True

        # TODO
        # 'su_zhan_su_jue', 'feng_chi_dian_che'
        # 'bao_ji_20'

    async def _enter_symk(self):
        await self._move_to_right_down()
        # await self.player.find_then_click('mo_ku_tan_xian')
        await self.player.click((635, 350))
        await self.player.monitor('ranking_icon4')
        pos_enter = (550, 435)
        await self.player.click(pos_enter)

        try:
            await self.player.find_then_click('skill_preview_btn', timeout=3)
        except FindTimeout:
            msg = "The shen yuan mo ku is not open yet."
            logger.info(msg)
            raise PlayException(msg)

    async def re_login(self):
        await self.goto_main_interface()
        await self.player.find_then_click('setting')
        await self.player.find_then_click('exit_btn')
        await self.player.find_then_click(OK_BUTTONS)
        await asyncio.sleep(5)    # 重新登陆多了，游戏会崩溃。所以试试延时
        await self.player.find_then_click('start_game')
        await self.player.find_then_click(['login_btn', 'login_btn2'])

        for _ in range(3):
            await asyncio.sleep(3)
            try:
                await self.player.find_then_click(['close_btn', 'close_btn5', 'start_game'], timeout=1)
            except FindTimeout:
                break    # 找不到 start_game，说明正在进入游戏，或已经进入游戏了

        await self.player.monitor('setting')


    async def ju_dian_gong_hui_zhan(self):
        if not await self._enter_ghz():
            return

        await self._pull_up_the_lens()

        for d in [None, 'left_top', 'left_down', 'right_down', 'right_top']:
            if d:
                await self._swip_to(d, stop=True)
                await asyncio.sleep(1)
                for g in await self.player.find_all_pos(['bao_xiang_guai', 'bao_xiang_guai1']):
                    await self.player.click(g)
                    await self.player.monitor(CLOSE_BUTTONS)
                    while True:
                        try:
                            await self.player.find_then_click(['tiao_zhan', 'tiao_zhan1'], timeout=1)
                        except FindTimeout:
                            await self.player.find_then_click(CLOSE_BUTTONS)
                            break
                        await self.player.monitor('dui_wu_xiang_qing')
                        await self.player.find_then_click('check_box', timeout=1, raise_exception=False)
                        try:
                            await self.player.find_then_click('tiao_zhan_start', timeout=1)
                        except FindTimeout:
                            return
                        await self.player.find_then_click(OK_BUTTONS)

    async def _enter_ghz(self):
        try:
            await self.player.find_then_click('ju_dian_ghz', timeout=1)
        except FindTimeout:
            return False

        name, pos = await self.player.monitor(['bao_ming', 'enter1'])
        if name == 'bao_ming':
            return False

        await self.player.click(pos)
        await asyncio.sleep(10)
        await self.player.monitor('jidi')
        return True

    async def _pull_up_the_lens(self):
        _, pos = await self.player.monitor('jidi')
        for _ in range(3):
            await self.player.scrool_with_ctrl(pos)
            try:
                await self.player.monitor('jidi_small', timeout=1)
                return True
            except FindTimeout:
                continue
        return False

    async def _close_game(self):
        pos_recent_tasks = (885, 500)
        pos_clear_all = (630, 85)
        await self.player.click(pos_recent_tasks, delay=2)
        await self.player.click(pos_clear_all)

    async def login(self, account_pre, account_curr):
        # account_curr = Account(game_name, account, passwd, server)
        async def _login_server():
            """login via another server, if sucess, return True"""
            if not account_curr.server:
                return True

            _, pos = await self.player.monitor(['setting'])
            await self.player.click(pos)
            _, pos = await self.player.monitor(['server_icon'])
            await self.player.click(pos)
            await self.player.monitor(['server_ui'])
            pos = await self.player.find_text_pos(account_curr.server)
            if pos == (-1, -1):
                self.logger.warning(
                    f"login server faild: can't find the {account_curr.server}")
                return False

            await self.player.click(pos)
            try:
                await self.player.monitor(['changge_server_remind'], timeout=1)
                pos_ok = (500, 350)
                await self.player.click(pos_ok)
                await asyncio.sleep(3)
                await self.player.monitor(['setting'])
                await self._close_ad()
            except FindTimeout:
                # 想登陆的区，正好是当前的区，直接返回
                await self.player.go_back()

            return True

        async def _login_account():
            """login via another account, if sucess, return True"""
            _, pos = await self.player.monitor(['setting'])
            await self.player.click(pos)
            await self.player.monitor(['server_icon'])
            pos_exit = (650, 350)
            await self.player.click(pos_exit)
            pos_ok = (500, 350)
            await self.player.click(pos_ok)
            pos_start_game = (430, 490)
            await self.player.click(pos_start_game)
            name, pos = await self.player.monitor(['setting', 'game_91'])

            if name == 'game_91':
                pos_account = (370, 235)
                await self.player.information_input(
                    pos_account, account_curr.user)
                await asyncio.sleep(1)
                pos_passwd = (370, 290)
                await self.player.information_input(
                    pos_passwd, account_curr.passwd)
                pos_login = (430, 340)
                await self.player.click(pos_login)
                await asyncio.sleep(3)
                name, pos = await self.player.monitor(['setting', 'game_91'])
                if name == 'game_91':
                    return False
                else:
                    await self._close_ad()
                    return True
            else:
                # 只有一个用户，直接进入游戏
                await self._close_ad()
                return True

        async def _login_game():
            """start game and login, if sucess, return True"""
            _, pos = await self.player.monitor([account_curr.game])

            # 同时启动，可能会导致闪退
            async with self.player.g_sem:
                await asyncio.sleep(5)
                await self.player.double_click(pos)

            await asyncio.sleep(30)

            await self.player.monitor(['close_btn', 'close_btn5', 'start_game'], timeout=120)

            for _ in range(3):
                await asyncio.sleep(3)
                try:
                    await self.player.find_then_click(['close_btn', 'close_btn5', 'start_game'], timeout=1)
                except FindTimeout:
                    break    # 找不到 start_game，说明正在进入游戏，或已经进入游戏了

            # for _ in range(5):
            #     try:
            #         name, pos = await self.player.monitor(['close_btn', 'close_btn5', 'start_game'])
            #         if name == 'start_game':
            #             await asyncio.sleep(2)
            #             name = await self.player.find_then_click(['close_btn', 'close_btn5', 'start_game'])
            #             if name == 'start_game':
            #                 break
            #         else:
            #             await self.player.click(pos)
            #     except FindTimeout:
            #         self.logger.warning("start game failed")
            #         return False

            #     await asyncio.sleep(2)

            # TODO: 账号异地登陆

            # pos_start_game = (430, 490)
            # await self.player.click(pos_start_game)
            # await asyncio.sleep(3)
            name, pos = await self.player.monitor(['setting', 'game_91'])
            if name == 'game_91':
                pos_login = (430, 350)
                await self.player.click(pos_login, delay=3)
                name, pos = await self.player.monitor(['setting', 'game_91'])
                if name == 'game_91':
                    self.logger.debug("_login_game failed.")
                    return False
                else:
                    await self._close_ad(timeout=5)
                    return True
            else:
                await self._close_ad(timeout=5)
                return True

        if not account_pre:
            sucess = await _login_game()
            if not sucess:
                await self._close_game()
                sucess = await _login_game()
                if not sucess:
                    return False

            # 现在，只有3个用户，不需要切换账号、服务器
            # await _login_account()
            # await _login_server()
        else:
            if account_curr.game != account_pre.game:
                await self._close_game()
                sucess = await _login_game()
                if not sucess:
                    await self._close_game()
                    sucess = await _login_game()
                    if not sucess:
                        return False
                # await _login_account()
                # await _login_server()
            # elif account_curr.account != account_pre.account:
            #     await _login_account()
            #     await _login_server()
            # else:
            #     await _login_server()

        return True

    async def play_game(self):
        task_list = [
            'MeiRiRenWu',
            'XianShiJie',
            'YouJian',
            'HaoYou',
            'SheQvZhuLi',
            'TiaoZhanFuben',
            'GongHui',
            'MeiRiQianDao',
            'JueDiKongJian',
            'ShengCunJiaYuan',
            'YaoQingYingXion',
            'WuQiKu',
            'XingCunJiangLi',
            'ShiChang',
            'JingJiChang',
            'GuanJunShiLian',
            'YongZheFuBen',
            'XingYunZhuanPan',
            'RenWuLan',
            'VipShangDian',
            'YingXiongYuanZheng',
            'MiGong',
            'RenWu',

        ]

        # task_list = [
        #     'ShenYuanMoKu',
        # ]

        restart_count = 0
        failed_task = set()

        self.player.load_role_cfg()

        for cls_name in task_list:
            self.logger.info("Start to run: " + cls_name)
            try:
                await self.goto_main_interface()
            except Exception as e:
                self.logger.error(str(e))
                self.save_operation_pics(str(e))
                success = await self.restart_game()
                if not success:
                    self.save_operation_pics(str(e))
                    # return False

            obj = getattr(tasks, cls_name)(self.player)
            try:
                await obj.run()
            except Exception as e:
                task_list.append(cls_name)
                self.logger.error(str(e))
                self.save_operation_pics(str(e))

                # TODO 如果累计timeout3次，也restart game
                if cls_name not in failed_task:
                    failed_task.add(cls_name)
                else:
                    if restart_count < 3:
                        self.logger.warning(
                            f'the {cls_name} failed again, so restart game')
                        restart_count += 1
                        success = await self.restart_game()
                        if not success:
                            self.save_operation_pics(str(e))
                            # return False
                    else:
                        self.logger.error('restart too many times, so exit')
                        # return False

        self.player.counter.save_data()

    async def restart_game(self):
        await self.player.find_then_click('recent_tasks')
        await self.player.find_then_click(['close6', 'close7'])
        _, pos = await self.player.monitor('mo_shi_jun_tun')

        await asyncio.sleep(5)
        await self.player.double_click(pos)

        await asyncio.sleep(50)

        await self.player.monitor(['close_btn', 'close_btn5', 'start_game'], timeout=90)

        for _ in range(3):
            await asyncio.sleep(3)
            try:
                await self.player.find_then_click(['close_btn', 'close_btn5', 'start_game'], timeout=1)
            except FindTimeout:
                break    # 找不到 start_game，说明正在进入游戏，或已经进入游戏了

        name, pos = await self.player.monitor(['setting', 'game_91'])
        if name == 'game_91':
            pos_login = (430, 350)
            await self.player.click(pos_login, delay=3)
            name, pos = await self.player.monitor(['setting', 'game_91'])
            if name == 'game_91':
                self.logger.debug("_login_game failed.")
                return False
            else:
                await self._close_ad(timeout=5)
                return True
        else:
            await self._close_ad(timeout=5)
            return True


def need_run(name):
    def is_pm():
        t = time.localtime()
        hour = t.tm_hour
        return hour > 12

    def is_odd_day():
        t = time.localtime()
        day = t.tm_mday
        return day % 2 == 1

    def is_sunday():
        t = time.localtime()
        # day of week, range [0, 6], Monday is 0
        wday = t.tm_wday
        return wday == 6

    if name == 'arena_champion':
        # return True
        if is_sunday() and is_pm():
            return True
        else:
            logger.debug(f"Skip to run {name}, for it isn't sunday PM now.")
            return False

    if name in ['arena', 'armory', 'invite_heroes', 'jedi_space', 'brave_instance', 'lucky_draw', 'task_board', 'vip_shop', 'tower_battle', 'maze', 'ju_dian_gong_hui_zhan']:
        # 只在下午运行
        if is_pm():
            return True
        else:
            logger.debug(f"Skip to run {name}, for it isn't PM now.")
            return False
    else:
        return True


async def play(window_name, account_list, g_queue, g_event, g_found, g_player_lock, g_sem):
    player = Player(window_name, g_queue, g_event,
                    g_found, g_player_lock, g_sem)
    auto_play = AutoPlay(player)

    # await auto_play.play_game()

    try:
        # 如果游戏已经启动，直接开玩
        await player.monitor(['setting'], timeout=1)
        return await auto_play.play_game()
    except FindTimeout:
        pass

    try:
        await player.monitor(['emulator_started'], timeout=60)
    except FindTimeout:
        logger.warning("Start the emulator failed.")
        return

    await asyncio.sleep(5)

    pos_close_remind = (680, 200)
    try:
        await player.monitor(['remind'], timeout=1)
        await player.click(pos_close_remind)
    except FindTimeout:
        pass

    pos_close_app = (300, 300)
    while True:
        try:
            await player.monitor(['app_error'], timeout=1)
            await player.click(pos_close_app)
        except FindTimeout:
            break

    account_pre = None
    Account = namedtuple(
        'Account', ['game', 'user', 'passwd', 'server'])

    while account_list:
        account_dict = account_list.pop()
        logger.debug(
            f'{window_name}: account_list: {account_list} account_dict: {account_dict}')
        logger.debug("remain account_list:" + str(len(account_list)))
        game = account_dict['game']
        user = account_dict['user']
        passwd = account_dict['passwd']
        server_ids = account_dict['server_ids']

        if server_ids:
            for server in server_ids:
                account_curr = Account(game, user, passwd, server)
                success = await auto_play.login(account_pre, account_curr)
                if not success:
                    logger.warning(f"{window_name} login failed.")
                    return
                account_pre = account_curr
                await auto_play.play_game()
        else:
            account_curr = Account(game, user, passwd, '')
            success = await auto_play.login(account_pre, account_curr)
            if not success:
                logger.warning(f"{window_name} login failed.")
                return
            account_pre = account_curr
            await auto_play.play_game()


# TODO  每个函数写的时候，就要考虑所有情况，不要都在测试的时候发现, 就该
#       要养成严谨的编程习惯

# TODO 建立数据库，配置文件，为每个角色建立基本信息
#      比如等级、今日任务是否完成 ……

# 很多图需要重新截图，因为窗口大小变了
# 原来是 910 * 520 现在是 960 * 550
# => 着是多开器搞的鬼，开2个窗口是 960 * 550， 3个则是910 * 520
# 记录下窗口大小参数，不确定的地方采用图像识别，别的一律用坐标
