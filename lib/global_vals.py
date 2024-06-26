##############################################################################
# 自定义异常
#
##############################################################################
class InternalError(Exception):
    """代码bug，需要迅速崩溃，然后修复"""

class EmulatorNotFound(Exception):
    pass

class EmulatorStartupTimeout(Exception):
    pass

class GameNotFound(Exception):
    pass

class UnsupportGame(Exception):
    pass

class LoginTimeout(Exception):
    pass

class RestartTooMany(Exception):
    pass

class UserConfigError(Exception):
    pass

class NotInGameMain(Exception):
    pass

class EmulatorSetError(Exception):
    pass

class MouseFailure(Exception):
    pass

class PlayException(Exception):
    pass

class FindTimeout(Exception):
    pass

class NoEnoughHero(Exception):
    pass

class NoEnoughXinFeng(Exception):
    pass

class NoEnoughZuanShi(Exception):
    pass

class NoEnoughSelfHero(Exception):
    pass

class NoEnoughGouLiang(Exception):
    pass

class NoEnoughHeroSpace(Exception):
    pass

class TextRecognitionFailure(Exception):
    pass

##############################################################################
# 全局常量
#
##############################################################################
WIDTH = 905
HIGH = 519

WINDOW_DICT = {
    'left_top': (0, 0),
    'left_down': (0, HIGH),
    'right_top': (WIDTH, 0),
    'full': (0, 0)
}

POS_DICT = {
    'ok': (430, 430),
    'next': (530, 430),
    'guild_territory': (700, 460),
    'donate_home': (770, 270),
    'exciting_activities': (740, 70),
    'sign_in': (700, 430),
    'challenge': (430, 450),
    'mop_up': (650, 150),
    'ok1': (420, 360),
    'ok_win': (430, 430),
    'ok_lose': (340, 430),
    'fight': (830, 490),
    'switch_map': (50, 470),
    '1_star': (520, 425),
    '2_star': (580, 425),
    'put_into': (150, 440),
    'dismiss': (320, 440),
    'quantity': (220, 330),
    'enter': (810, 480),
    'forging': (250, 450),
    'get_gold': (410, 50),
    'refresh': (660, 170),
    'box': (750, 470),
    'select_gift': (70, 450),
    'send_gift': (810, 450),
}

SCREEN_DICT = {
    'screen': './pics/screen.jpg',
    'screen_left_top': './pics/screen_left_top.jpg',
    'screen_left_down': './pics/screen_left_down.jpg',
    'screen_right_top': './pics/screen_right_top.jpg',
}

OK_BUTTONS = [
    'ok',
    'ok3',
    'ok5',
    'ok8',
    'ok9',
    'ok10',
    'ok_btn1',
    'que_ding2'
]

CLOSE_BUTTONS = [
    'close',
    'close_btn',
    'close_btn1',
    'close_btn2',
    'close_btn3',
    'close_btn4',
]

GOOD_TASKS = [
    'task_3star',
    'task_4star',
    'task_5star',
    'task_6star',
    'task_7star'
]
