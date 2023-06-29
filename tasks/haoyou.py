import asyncio

from lib.global_vals import *
from tasks.task import Task


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
