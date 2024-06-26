##############################################################################
# 自动截取英雄名字和脸部图片
#
##############################################################################

import asyncio
import os
import sys
import numpy as np
import cv2
from lib import windows
from lib.player import Player, FindTimeout
from PIL import ImageGrab
from time import sleep


# 切换到脚本所在目录
# 否则，基于相对路径的代码会出问题
main_dir = os.path.split(os.path.realpath(__file__))[0]
os.chdir(main_dir)
sys.path.insert(0, main_dir)

window = windows.Window('left_top')
player = Player(g_lock=asyncio.Lock(), window=window)

hero_dir = os.path.join(main_dir, 'pics', 'heroes_test')

# 有些英雄face1和face2合并了，也有些英雄有其它皮肤
face_names = {
    '5x': '1face', 
    '6x': '2face',
    '10x': '3face',
}

# 截取英雄头像并保存
async def main():
    await player.find_then_click('ying_xiong')
    await player.find_then_click('yingxiongtujian')

    # for zhen_ying in ['sh', 'zx', 'hd', 'xe']:
    for zhen_ying in ['xe']:
        await player.find_then_click(f"{zhen_ying}_L")
        await asyncio.sleep(1)

        # 阵营_序号_星级
        all_heroes = get_known_heroes(hero_dir, zhen_ying)
        if all_heroes:
            hero_names = [i for i in all_heroes if not i.endswith('x')]
            max_num = int(sorted(list(hero_names))[-1].split('_')[1])
        else:
            hero_names = []
            max_num = 0

        while True:
            reach_down = await swipe_up()
            if reach_down:
                break

        reach_top = False
        while True:
            for xing in ['5x', '6x', '10x']:
                if not player.is_exist(xing):
                    continue

                pos_list = await player.find_all_pos(xing, threshold=0.9)
                for pos in sorted(pos_list, key=lambda x: (round(x[1] / 10), x[0]), reverse=True):
                    # round 是为了避免一两个像素的误差，而导致顺序错误
                    await player.monitor('yingxiongtujian')
                    await player.click((pos[0], pos[1]-35))
                    await player.monitor('i')

                    if hero_names:
                        if await is_known_name(hero_names):
                            num = await get_num(hero_names)
                        else:
                            max_num += 1
                            num = max_num
                            name = f"{zhen_ying}_{str(num).zfill(2)}"
                            await save_hero_name(name)
                            hero_names.append(name)
                    else:
                        max_num += 1
                        num = max_num
                        name = f"{zhen_ying}_{str(num).zfill(2)}"
                        await save_hero_name(name)
                        hero_names.append(name)

                    await player.go_back()
                    await player.monitor('yingxiongtujian')
                    await save_hero_icon(pos, f"{zhen_ying}_{str(num).zfill(2)}_{xing}")
                    await save_hero_face(pos, f"{zhen_ying}_{str(num).zfill(2)}_{face_names[xing]}")
                    
            
            if reach_top:
                # 上一次已经到达顶部了，说明全部截图完成了
                break
            reach_top = await swipe_down()


def get_known_heroes(hero_dir, zhen_ying):
    all_heroes = set()
    for root, dirs, files in os.walk(hero_dir):
        for f in files:
            name, ext = os.path.splitext(f)
            if name.startswith(zhen_ying):
                all_heroes.add(name)
    return all_heroes


async def is_known_name(known_names):
    try:
        await player.monitor(known_names, timeout=2)
        return True
    except FindTimeout:
        return False


async def save_hero_name(name):
    img = ImageGrab.grab(bbox=(590, 142, 670, 165))
    # img_np = np.array(img)
    # rgb_img = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
    path = os.path.join(hero_dir, f"{name}.jpg")
    img.save(path)
    # cv2.imwrite(path, img)


async def save_hero_icon(pos, name):
    """带上星星的脸"""
    x, y = pos
    # bbox = (x-20, y-30, x+20, y)
    bbox = (x-23, y-35, x+24, y)
    img = ImageGrab.grab(bbox=bbox)
    path = os.path.join(hero_dir, f"{name}.jpg")
    img.save(path)

async def save_hero_face(pos, name):
    x, y = pos
    bbox = (x-20, y-45, x+20, y-15)
    img = ImageGrab.grab(bbox=bbox)
    path = os.path.join(hero_dir, f"{name}.jpg")
    img.save(path)


async def get_num(known_names):
    name, _ = await player.monitor(known_names, timeout=2)
    num = name.split('_')[-1]
    return num

async def swipe_down():
    p1 = (740, 155)
    p2 = (740, 480)
    res = await drag_then_find(p1, p2, 'reach_top')
    sleep(1)
    return res

async def swipe_up():
    p1 = (740, 480)
    p2 = (740, 155)
    res = await drag_then_find(p1, p2, 'reach_down')
    return res

async def drag_then_find(p1, p2, pic):
    await player.hand.drag_and_keep(p1, p2)
    res = player.is_exist(pic, threshold=0.92)
    await player.hand.release_mouse(p2)
    return res

if __name__ == '__main__':
    asyncio.run(main())
