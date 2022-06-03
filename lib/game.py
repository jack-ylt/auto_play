##############################################################################
# 主要用于操作游戏：登陆、重启等
#
##############################################################################

import asyncio
import logging
from lib.player import Player, FindTimeout
from lib.ui_data import OK_BUTTONS, CLOSE_BUTTONS
from lib.windows import Window


# TODO 如何支持不同的game ico？
class Game(object):
    def __init__(self, player):
        self.player = player
        self.restart_count = 0
        self.logger = player.logger

    async def get_account(self):
        self.logger.info("get_account")
        await self._logout()
        await self.player.find_then_click('start_game')
        await self.player.monitor('game_91_2')

        pos_user = (370, 235)
        account = await self.player.copy_input(pos_user)
        self.logger.debug(f"get account: {account}")

        await self.player.find_then_click('login_btn')
        await self.player.monitor('setting')

        return account

    async def game_started(self):
        try:
            await self.player.monitor('setting', timeout=1)
            return True
        except FindTimeout:
            return False

    async def restart_game(self, game):
        self.logger.info("restart game")
        self.restart_count += 1
        await self._close_game(game)
        await self.start_game(game)
        

    async def start_game(self, game):
        self.logger.info("start_game")
        _, pos = await self.player.monitor(game)
        await asyncio.sleep(3)
        await self.player.double_click(pos)

        await asyncio.sleep(50)
        await self.player.monitor(['close_btn', 'close_btn5', 'start_game'], timeout=90)

        for _ in range(3):
            await asyncio.sleep(3)
            try:
                await self.player.find_then_click(['close_btn', 'close_btn5', 'start_game'], timeout=1)
            except FindTimeout:
                break    # 找不到 start_game，说明正在进入游戏，或已经进入游戏了

        # TODO game_91 需要适配多平台
        name, pos = await self.player.monitor(['setting', 'game_91_2'])
        if name == 'game_91_2':
            pos_login = (430, 350)
            await self.player.click(pos_login, delay=3)
            name, pos = await self.player.monitor(['setting', 'game_91_2'])
            if name == 'game_91_2':
                self.logger.debug("_login_game failed.")
                return False
            else:
                await self._close_ad(timeout=5)
                return True
        else:
            await self._close_ad(timeout=5)
            return True

    async def _close_ad(self, timeout=2):
        try:
            _, pos = await self.player.monitor(['close_btn1', 'close_btn2', 'close_btn3'], timeout=timeout)
            await self.player.click(pos)
        except FindTimeout:
            pass


    async def _close_game(self, game):
        await self.player.find_then_click('recent_tasks')
        await self.player.find_then_click(['close6', 'close7'])
        _, pos = await self.player.monitor(game)


    async def switch_account_login(self, game, user, passwd):
        self.logger.info('switch_account_login')
        await self._logout()
        await self._login(game, user, passwd)

    async def _logout(self):
        await self.player.find_then_click('setting')
        await self.player.find_then_click('tui_chu')
        await self.player.find_then_click(OK_BUTTONS)

    # TODO 目前还不支持切换game登录
    async def _login(self, game, user, passwd):
        await self.player.find_then_click('start_game')
        await self.player.monitor('game_91_2')

        pos_user = (370, 235)
        await self.player.information_input(pos_user, user)
        pos_passwd = (370, 290)
        await self.player.information_input(pos_passwd, passwd)

        await self.player.find_then_click('login_btn')
        await self.player.monitor('setting')

    async def goto_main_interface(self, game):
        """通过esc回主界面

        如果esc不行，则业务要自己回主界面
        """
        self.logger.debug('goto_main_interface')
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
            self.logger.error("go to main interface failed, so restart game")
            await self._close_game(game)
            await self.start_game(game)
