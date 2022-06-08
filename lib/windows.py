

class Window(object):
    WIDTH = 905
    HIGH = 519

    # START_POS = {
    #     'left_top': (0, 0),
    #     'left_down': (0, HIGH),
    #     'right_top': (WIDTH, 0),
    #     'full': (0, 0)
    # }

    BBOX = {
        'left_top': (0, 0, WIDTH, HIGH),
        'left_down': (0, HIGH, WIDTH, HIGH * 2),
        'right_top': (WIDTH, 0, WIDTH * 2, HIGH),
        'full': (0, 0, WIDTH * 2, HIGH * 2)
    }

    def __init__(self, name):
        self.name = name
        # self.left, self.top = self.START_POS[name]
        # self.right, self.bottom = self.left + self.WIDTH, self.top + self.HIGH
        # self.bbox = (self.left, self.top, self.right, self.bottom)
        self.bbox = self.BBOX[self.name]
    
    def __eq__(self, other):
        return self.name == other.name

    def __str__(self):
        return f"{self.name} window"

    def in_window(self, pos):
        x, y = pos
        # x0, y0 = self.START_POS[self.name]
        # x1 = x0 + self.WIDTH
        # y1 = y0 + self.HIGH
        x0, y0, x1, y1 = self.bbox
        return x0 < x < x1 and y0 < y < y1

    def real_pos(self, pos):
        """current window pos -> computer screen pos"""
        x, y = pos
        # dx, dy = self.START_POS[self.name]
        dx, dy, _, _ = self.bbox
        return (x + dx, y + dy)
