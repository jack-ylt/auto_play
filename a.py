
import random

def _select_equipment_randomly():
    """随机选择锻造装备，不能每次都薅同一只羊"""
    pos_types = [
        (820, 190),
        (820, 270),
        (820, 350),
        (820, 440),
    ]
    seen = set()

    def _select():
        while True:
            if len(seen) == len(pos_types):
                return ()
            pos = random.choice(pos_types)
            if pos not in seen:
                seen.add(pos)
                return pos

    return _select()

for _ in range(5):
    print(_select_equipment_randomly())