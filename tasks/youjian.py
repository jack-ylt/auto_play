

from lib.global_vals import *
from tasks.task import Task


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
