
from numpy import histogram
from ui_data import HIGH, WIDTH, WINDOW_DICT

def get_window_region(window_name):
    x, y = WINDOW_DICT[window_name]
    w, h = WIDTH, HIGH
    return (x, y, x+w, y+h)
