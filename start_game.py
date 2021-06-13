from ui_data import POS_DICT
import player_hand
import player_eye
import asyncio
import logging
logger = logging.getLogger(__name__)


eye = player_eye.Eye()
hand = player_hand.Hand()


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
    await hand.click(pos_select_all)
    await asyncio.sleep(1)
    await hand.click(pos_start)
    # await asyncio.sleep(3)
    # await hand.click(pos_minimize)

    await asyncio.sleep(20)

