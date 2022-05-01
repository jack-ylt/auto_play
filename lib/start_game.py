from gettext import find
from lib.ui_data import POS_DICT
from lib import player_hand
from lib import player_eye
from lib import player
import asyncio
import logging
logger = logging.getLogger(__name__)


eye = player_eye.Eye()
hand = player_hand.Hand()

p = player.Player()


async def game_started():
    try:
        await p.monitor('setting', timeout=1)
        return True
    except player_eye.FindTimeout:
        return False


async def start_emulator():
    try:
        _, pos = await p.monitor(['emulator_icon'])
    except player_eye.FindTimeout:
        logger.info("Start emulator failed: can't find the emulator_icon")
        return False

    await hand.double_click(pos)

    await asyncio.sleep(3)
    _, pos = await p.monitor(['duo_kai_guang_li'], timeout=10)
    await hand.click(pos)

    try:
        _, pos = await p.monitor('select_all', timeout=1)
        await hand.click(pos)
    except player_eye.FindTimeout:
        pass

    await asyncio.sleep(1)
    pos_start = (600, 270)
    await hand.click(pos_start, cheat=False)

    await asyncio.sleep(20)
