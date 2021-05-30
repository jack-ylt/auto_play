# WIDTH = 910
# HIGH = 518

# WINDOW_DICT = {
#     'left_top': (0, 0),
#     'left_down': (0, 518)
# }
from numpy import histogram
from ui_data import HIGH, WIDTH, WINDOW_DICT

def get_window_region(window_name):
    x, y = WINDOW_DICT[window_name]
    w, h = WIDTH, HIGH
    return (x, y, x+w, y+h)
