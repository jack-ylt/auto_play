from lib.ui_data import POS_DICT
from lib import player_hand
from lib import player_eye
import asyncio
import logging
logger = logging.getLogger(__name__)


eye = player_eye.Eye()
hand = player_hand.Hand()

def game_started():
    try:
        player_eye.monitor(['setting'])
        return True
    except player_eye.FindTimeout:
        return False
    


async def start_emulator():
    try:
        _, pos = player_eye.monitor(['emulator_icon'])
    except player_eye.FindTimeout:
        logger.info("Start emulator failed: can't find the emulator_icon")
        return False
    # await hand.click(pos, delay=0.3)
    # await hand.click(pos, delay=0.3)
    await hand.double_click(pos)

    await asyncio.sleep(3)
    _, pos = player_eye.monitor(['emulator_ui'], timeout=10)
    pos_select_all = (590, 312)
    pos_start = (600, 270)
    pos_minimize = (1300, 225)
    await hand.click(pos_select_all, cheat=False)
    await asyncio.sleep(1)
    await hand.click(pos_start, cheat=False)
    # await asyncio.sleep(3)
    # await hand.click(pos_minimize)

    await asyncio.sleep(20)

