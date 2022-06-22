"""
主要用于操作游戏：
- 登陆
- 重启
- 回到游戏主界面

"""

import asyncio
from lib.player import FindTimeout
from lib.ui_data import OK_BUTTONS, CLOSE_BUTTONS


# 每种游戏，创建一个类。使用代理模式

class Gamer(object):
    def __init__(self, player, role):
        self._real_gamer = self._get_real_gamer(player, role)

    def _get_real_gamer(self, player, role):
        gamer_dict = {
            'mo_ri_xue_zhan_jiuyou': GamerMrxzJy,
            'mo_ri_xue_zhan_mihoutao': GamerMrxzMht,
            'mo_ri_xue_zhan_changxiang': GamerMrxzCx,
            'mo_shi_jun_tun': GamerMsjt,
        }
        return gamer_dict[role.game](player, role)

    async def login(self):
        await self._real_gamer.login()

    async def restart(self):
        await self._real_gamer.restart()

    async def goto_main_ui(self):
        await self._real_gamer.goto_main_ui()


class GamerBase(object):
    def __init__(self, player, role):
        self.player = player
        self.role = role
        self.logger = player.logger

    async def goto_main_ui(self):
        """回游戏主界面

        如果esc不行，则业务要自己回主界面
        """
        self.logger.debug('goto game main ui')
        for _ in range(5):
            try:
                await self.player.monitor('setting', timeout=2)
            except FindTimeout:
                await self.player.go_back()    # ESC 可能失效 (游戏未响应)
            else:
                break

        await self._close_ad(timeout=2)
        await self.player.monitor('setting', timeout=1)

    async def restart(self):
        """游戏异常就重启游戏"""
        self.logger.info("restart game")
        await self._close_game()
        await self._login_game(change_account=False)

    async def login(self):
        """使用role登录游戏"""
        self.logger.info(f"login for {self.role}")

        if await self._at_emulator_main():
            await self._login_game()
        else:
            try:
                await self.goto_main_ui()
            except FindTimeout:
                self.logger.warning("goto main failed, so close game then login.")
                await self._close_game()
                await self._login_game()
            else:
                game_curr = await self._get_curr_game()
                if game_curr == self.role.game:
                    await self._switch_account()
                else:
                    await self._close_game()
                    await self._login_game()

    async def _at_emulator_main(self):
        try:
            await self.player.monitor('emulator_started', timeout=1)
            return True
        except FindTimeout:
            return False

    async def _login_game(self, change_account=True):
        raise NotImplementedError()

    async def _launch_game(self):
        _, pos = await self.player.monitor(self.role.game, timeout=2, interval=0.3)
        # await asyncio.sleep(3)    # 这边等3s，导致主控那边重复found同一个窗口，导致left_down没有启动到
        await self.player.double_click(pos)
        # 如果双击没反应，就再试一次
        if not await self.player.wait_disappear(self.role.game):
            await self.player.double_click(pos)

        await asyncio.sleep(30)
        await self.player.monitor(['close_btn', 'close_btn5', 'start_game'], timeout=90)

        await asyncio.sleep(1)
        for _ in range(3):
            await asyncio.sleep(1)
            name = await self.player.find_then_click(
                ['close_btn', 'close_btn5', 'start_game'], timeout=1, delay=0.3)
            if name == 'start_game':
                break

    async def _close_game(self):
        await self.player.find_then_click('recent_tasks', cheat=False)
        # await self.player.find_then_click(['close6', 'close7'])
        await self.player.find_then_click('quan_bu_qing_chu', cheat=False)

        await self.player.monitor('emulator_started')

    async def _get_curr_game(self):
        game_dict = {
            'mo_ri_xue_zhan_jiuyou_title': 'mo_ri_xue_zhan_jiuyou',
            'mo_ri_xue_zhan_mihoutao_title': 'mo_ri_xue_zhan_mihoutao',
            'mo_ri_xue_zhan_changxiang_title': 'mo_ri_xue_zhan_changxiang',
            'mo_shi_jun_tun_title': 'mo_shi_jun_tun',
        }
        await self.player.find_then_click('recent_tasks', cheat=False )
        name, _ = await self.player.monitor(list(game_dict))
        await asyncio.sleep(1)
        await self.player.find_then_click('recent_tasks', cheat=False)
        return game_dict[name]

    async def _switch_account(self):
        await self._logout()
        await self.player.find_then_click('start_game')
        await self._enter_account_info()
        await self.player.monitor('setting', timeout=15)
        await self._close_ad(timeout=5)

    async def _logout(self):
        await self.player.find_then_click('setting')
        await self.player.find_then_click('tui_chu')
        await self.player.find_then_click(OK_BUTTONS)

    async def _enter_account_info(self):
        raise NotImplementedError()

    async def _close_ad(self, timeout=2):
        cloes_btns = ['close_btn1', 'close_btn2', 'close_btn3', 'close9', 'close_btn4']
        for _ in range(3):
            try:
                _, pos = await self.player.monitor(cloes_btns, timeout=timeout)
                await self.player.click(pos)
            except FindTimeout:
                break


class GamerMrxzJy(GamerBase):
    """gamer class of 末日血战-九游"""

    async def _login_game(self, change_account=True):
        await self._launch_game()

        # 如果打开游戏，有可能显示qie_huan_zhang_hao，然后自动登录，也有可能直接显示qi_ta_zhang_hao
        # 如果是退出登录，再登陆，会显示qie_huan_zhang_hao
        if change_account:
            await self._enter_account_info()
        else:
            try:
                await self.player.monitor('qi_ta_zhang_hao', timeout=2)
                await self.player.click((400, 190))    # 点击第一个账号
            except FindTimeout:
                pass

        await self.player.monitor('setting', timeout=15)
        await self._close_ad(timeout=5)

    async def _enter_account_info(self):
        # interval 小一点，以防来不及
        await self.player.find_then_click('qie_huan_zhang_hao', raise_exception=False, timeout=2, interval=0.3)
        await self.player.find_then_click('qi_ta_zhang_hao')
        await self.player.find_then_click('mi_ma_deng_lu')

        await asyncio.sleep(1)
        pos_user = (430, 254)
        await self.player.information_input(pos_user, self.role.user)
        pos_passwd = (430, 308)
        await self.player.information_input(pos_passwd, self.role.passwd)

        await self.player.find_then_click('deng_lu')


class GamerMrxzMht(GamerBase):
    """gamer class of 末日血战-猕猴桃"""

    async def _login_game(self, change_account=True):
        await self._launch_game()

        # 如果打开游戏，有可能显示qie_huan_zhang_hao_mht，然后自动登录，也有可能直接显示qi_ta_zhang_hao_mht
        # 如果是退出登录，再登陆，会显示qie_huan_zhang_hao_mht
        if change_account:
            await self._enter_account_info()
        else:
            try:
                await self.player.monitor('qi_ta_zhang_hao_mht', timeout=2)
                await self.player.click((400, 190))    # 点击第一个账号
            except FindTimeout:
                pass

        await self.player.monitor('setting', timeout=15)
        await self._close_ad(timeout=5)

    async def _enter_account_info(self):
        await self.player.find_then_click('qie_huan_zhang_hao_mht', raise_exception=False, timeout=2, interval=0.3)
        await self.player.find_then_click('qi_ta_zhang_hao_mht', raise_exception=False, timeout=2)
        await self.player.find_then_click('mi_hou_tao')

        await self.player.monitor('mi_hou_tao_s')
        await asyncio.sleep(1)
        pos_user = (400, 220)
        await self.player.information_input(pos_user, self.role.user)
        pos_passwd = (400, 280)
        await self.player.information_input(pos_passwd, self.role.passwd)

        await self.player.find_then_click('deng_lu_mht')


class GamerMrxzCx(GamerBase):
    """gamer class of 末日血战-畅想"""

    async def _login_game(self, change_account=True):
        await self._launch_game()

        if change_account:
            await self._enter_account_info()
        else:
            await self.player.monitor('kui_su_deng_lu')

        await self.player.monitor('setting', timeout=15)
        await self._close_ad(timeout=5)

    async def _enter_account_info(self):
        await self.player.monitor('kui_su_deng_lu')

        await asyncio.sleep(1)
        pos_user = (380, 215)
        await self.player.information_input(pos_user, self.role.user)
        pos_passwd = (380, 265)
        await self.player.information_input(pos_passwd, self.role.passwd)

        await self.player.find_then_click('kui_su_deng_lu')


class GamerMsjt(GamerBase):
    """gamer class of 末世军团"""

    async def _login_game(self, change_account=True):
        need_switch_account = False

        await self._launch_game()

        try:
            await self.player.monitor('login_btn', timeout=2)
        except FindTimeout:
            if change_account:
                need_switch_account = True
        else:
            if change_account:
                await self._enter_account_info()
            else:
                await self.player.find_then_click('login_btn')

        await self.player.monitor('setting', timeout=15)
        await self._close_ad(timeout=5)

        if need_switch_account:
            await self._switch_account()

    async def _enter_account_info(self):
        await self.player.monitor('login_btn')

        await asyncio.sleep(1)
        pos_user = (370, 235)
        await self.player.information_input(pos_user, self.role.user)
        pos_passwd = (370, 290)
        await self.player.information_input(pos_passwd, self.role.passwd)

        await self.player.find_then_click('login_btn')
