# -*-coding:utf-8-*-

##############################################################################
# 主要用于监控游戏状态，以及文字识别
# 给定一些图片（可以附加区域信息），能判断当前画面中含有哪个图片，以及位置在哪
# 给定一个区域，能识别该区域中的文字信息
#
##############################################################################

import logging
import cv2
import re
import numpy as np
from PIL import ImageGrab, Image
from time import sleep, time
from aip import AipOcr
from datetime import date
import os

# TODAY = str(date.today())
# LOG_FILE = 'log_' + TODAY + '.log'


logger = logging.getLogger(__name__)

config = {
    'appId': '14224264',
    'apiKey': 'acb29MRO413yLSuTkC2TIfXd',
    'secretKey': '2abIQ9DTiBaZTK1FrKx1OqGzIbT2pVGW'}
client = AipOcr(**config)
options = {
    'probability': 'true',
    'detect_language': 'true'}

# {name: pic_path, ...}
PIC_DICT = {
    'screen': './pics/screen.jpg',

    # fight
    'fight': './pics/fight/fight.jpg',
    'fight1': './pics/fight/fight1.jpg',
    'skip_fight': './pics/fight/skip_fight.jpg',
    'start_fight': './pics/fight/start_fight.jpg',
    'fast_forward': './pics/fight/fast_forward.jpg',
    'fast_forward1': './pics/fight/fast_forward1.jpg',
    'go_last': './pics/fight/go_last.jpg',
    'win': './pics/fight/win.jpg',
    'lose': './pics/fight/lose.jpg',
    'ok': './pics/fight/ok.jpg',
    'card': './pics/fight/card.jpg',
    

    # level_battle
    'level_battle': './pics/level_battle/level_battle.jpg',
    # 'box': './pics/level_battle/box.jpg',
    # 'box1': './pics/level_battle/box1.jpg',
    # 'box2': './pics/level_battle/box2.jpg',
    'receive': './pics/level_battle/receive.jpg',
    'upgraded': './pics/level_battle/upgraded.jpg',
    'map_unlocked': './pics/level_battle/map_unlocked.jpg',
    'next_level1': './pics/level_battle/next_level1.jpg',
    'search': './pics/level_battle/search.jpg',
    'level_map': './pics/level_battle/level_map.jpg',
    'point': './pics/level_battle/point.jpg',
    'ok1': './pics/level_battle/ok1.jpg',
    'already_passed': './pics/level_battle/already_passed.jpg',
    'next_level2': './pics/level_battle/next_level2.jpg',
    'next_level3': './pics/level_battle/next_level3.jpg',

    # warriors_tower
    'warriors_tower': './pics/warriors_tower/warriors_tower.jpg',
    'challenge': './pics/warriors_tower/challenge.jpg',

    # main_interface
    "setting": "./pics/main_interface/setting.jpg",
    # "mail": "./pics/main_interface/mail.jpg",
    # "friends": "./pics/main_interface/friends.jpg",
    
    
    "community_assistant": "./pics/main_interface/community_assistant.jpg",
    # "challenge1": "./pics/main_interface/challenge.jpg",

    # mail
    "mail": "./pics/mail/mail.jpg",
    "one_click_collection": "./pics/mail/one_click_collection.jpg",
    
    # friends
    "friends": "./pics/friends/friends.jpg",
    "receive_and_send": "./pics/friends/receive_and_send.jpg",
    "30_friends": "./pics/friends/30_friends.jpg",
    "apply": "./pics/friends/apply.jpg",
    "friends_help": "./pics/friends/friends_help.jpg",
    "search1": "./pics/friends/search1.jpg",
    "fight2": "./pics/friends/fight2.jpg",
    "fight3": "./pics/friends/fight3.jpg",
    "ok2": "./pics/friends/ok2.jpg",


    # community_assistant
    "guess_ring": "./pics/community_assistant/guess_ring.jpg",
    "cup": "./pics/community_assistant/cup.jpg",
    "next_game": "./pics/community_assistant/next_game.jpg",
    "have_a_drink": "./pics/community_assistant/have_a_drink.jpg",
    "gift": "./pics/community_assistant/gift.jpg",
    "start_turntable": "./pics/community_assistant/start_turntable.jpg",
    "gift_over": "./pics/community_assistant/gift_over.jpg",

    # Instance_challenge
    "Instance_challenge": "./pics/instance_challenge/Instance_challenge.jpg",
    "challenge2": "./pics/instance_challenge/challenge.jpg",
    "challenge3": "./pics/instance_challenge/challenge1.jpg",
    "mop_up": "./pics/instance_challenge/mop_up.jpg",
    "next_game1": "./pics/instance_challenge/next_game.jpg",
    "ok3": "./pics/instance_challenge/ok.jpg",

    # guild
    "guild": "./pics/guild/guild.jpg",
    "sign_in": "./pics/guild/sign_in.jpg",
    "guild_instance": "./pics/guild/guild_instance.jpg",
    "boss_card": "./pics/guild/boss_card.jpg",
    "fight4": "./pics/guild/fight.jpg",
    "fight5": "./pics/guild/fight1.jpg",
    "ok4": "./pics/guild/ok.jpg",
    "ok5": "./pics/guild/ok1.jpg",
    "guild_factory": "./pics/guild/guild_factory.jpg",
    "get_order": "./pics/guild/get_order.jpg",
    "start_order": "./pics/guild/start_order.jpg",
    "donate": "./pics/guild/donate.jpg",

    # jedi_space
    "jedi_space": "./pics/jedi_space/jedi_space.jpg",
    "plus": "./pics/jedi_space/plus.jpg",

    # survival_home
    "survival_home": "./pics/survival_home/survival_home.jpg",
    "gold": "./pics/survival_home/gold.jpg",
    "food": "./pics/survival_home/food.jpg",
    "oil": "./pics/survival_home/oil.jpg",
    "box": "./pics/survival_home/box.jpg",
    "boss": "./pics/survival_home/boss.jpg",
    "switch_map": "./pics/survival_home/switch_map.jpg",
    "field_map": "./pics/survival_home/field_map.jpg",
    "fight6": "./pics/survival_home/fight.jpg",

    # invite_hero
    "invite_hero": "./pics/invite_hero/invite_hero.jpg",
    "invite_free": "./pics/invite_hero/invite_free.jpg",
    "invite_soda": "./pics/invite_hero/invite_soda.jpg",
    "invite_beer": "./pics/invite_hero/invite_beer.jpg",
    "ok6": "./pics/invite_hero/ok.jpg",

    # armory
    "armory": "./pics/armory/armory.jpg",
    "arms": "./pics/armory/arms.jpg",

    # market
    "market": "./pics/market/market.jpg",
    "refresh": "./pics/market/refresh.jpg",
    "refresh1": "./pics/market/refresh1.jpg",
    "refresh2": "./pics/market/refresh2.jpg",
    "refresh3": "./pics/market/refresh3.jpg",
    "get_for_free": "./pics/market/get_for_free.jpg",
    "get_for_free1": "./pics/market/get_for_free1.jpg",
    "get_for_free2": "./pics/market/get_for_free2.jpg",
    "ok7": "./pics/market/ok.jpg",
    "ok8": "./pics/market/ok8.jpg",
    "ok9": "./pics/market/ok9.jpg",
    "lack_of_gold": "./pics/market/lack_of_gold.jpg",

    "hero_badge": "./pics/market/hero_badge.jpg",
    "task_ticket": "./pics/market/task_ticket.jpg",
    "soda_water1": "./pics/market/soda_water1.jpg",
    "soda_water2": "./pics/market/soda_water2.jpg",
    "soda_water3": "./pics/market/soda_water3.jpg",

    "hero_shard_3_1": "./pics/market/hero_shard_3_1.jpg",
    "hero_shard_3_2": "./pics/market/hero_shard_3_2.jpg",
    "hero_shard_3_3": "./pics/market/hero_shard_3_3.jpg",
    "hero_shard_3_4": "./pics/market/hero_shard_3_4.jpg",
    "hero_shard_4_1": "./pics/market/hero_shard_4_1.jpg",
    "hero_shard_4_2": "./pics/market/hero_shard_4_2.jpg",
    "hero_shard_4_3": "./pics/market/hero_shard_4_3.jpg",

    # arena
    "arena": "./pics/arena/arena.jpg",
    "enter": "./pics/arena/enter.jpg",
    "fight7": "./pics/arena/fight.jpg",
    "fight8": "./pics/arena/fight1.jpg",

}



class Eye(object):
    def __init__(self):
        self.img_dict = {}    # {name: img_obj, ...}
        self._load_target_imgs()

    def _load_target_imgs(self):
        for name, path in PIC_DICT.items():
            img = self.read_pic(path)
            self.img_dict[name] = img

    def screenshot(self, name):
        """screenshot, and save as file."""
        im = ImageGrab.grab()
        im.save(name)
        img_rgb = cv2.imread(name)
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        return img_gray

    def read_pic(self, pic_path):
        """read pic file, return img_gray object"""
        # img_rgb = cv2.imread(pic_path)
        # img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        if not os.path.exists(pic_path):
            raise Exception(f"The {pic_path} isn't exists.")
        img = cv2.imread(pic_path, 0)
        return img



    def de_duplication(self, pos_list, offset=3):
        """去掉匹配到的重复的图像坐标"""
        new_list = []

        for (x, y) in pos_list:
            if not new_list:
                new_list.append((x, y))
            else:
                for (x1, y1) in new_list[:]:
                    if x1 - offset < x < x1 + offset and \
                        y1 - offset < y < y1 + offset :
                        break
                else:
                    new_list.append((x, y))

        return new_list

    def to_center_pos(self, pos_list, img_target):
        """转化为图像中心的坐标"""
        h, w = img_target.shape

        for i, pos in enumerate(pos_list):
            x = int(pos[0] + (w / 2))
            y = int(pos[1] + (h / 2))
            pos_list[i] = (x, y)

        return pos_list
        


    def find_img_pos(self, img_bg, img_target, threshold=0.9):
        """find the position of the target_image in background_image.

        return a list of postions
        """
        res = cv2.matchTemplate(img_bg, img_target, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        locs = np.where(res >= threshold)
        if len(locs[0]) == 0:
            return []

        pos_list = list(zip(*locs[::-1]))
        pos_list.insert(0, max_loc)    # 使得默认能获取匹配度最高的位置
        pos_list = self.de_duplication(pos_list)
        pos_list = self.to_center_pos(pos_list, img_target)
        # logger.debug(f"pos_list: {pos_list}")
        print('max_val:', max_val, 'max_loc', max_loc)
        return pos_list

        # TODO 返回 去重后的 中心坐标 pos_list 就好，过滤交给业务去做
    def cut_image(self, image, x, y, w, h):
        """cut image file according to (left top width hight)"""
        region = image.crop((x, y, x+w, y+h))
        return region

    # def _pic_to_word(self, name):
    #     """get a word from a pic file

    #     note only get one words (if have manyy words, join them with ' '.
    #     (pic) -> str
    #     """
    #     words = []
    #     with open(name, 'rb') as fp:
    #         image = fp.read()
    #     result = client.basicGeneral(image, options)    # 50000/day
    #     #result = client.basicAccurate(image, options)   # 500/day

    #     if 'words_result' in result:
    #         for i in result['words_result']:
    #             word = i['words']
    #             probability = i['probability']['average']
    #             print("word: {}, probalility: {}".format(word, probability))
    #             if probability >= 0.8:
    #                 words.append(word.strip())

    #     return ' '.join(words).strip()

    # def get_text(self, name, region):
    #     """recognise all texts in a region of current game image"""
    #     self._cut_image(name, *region)
    #     for i in range(3):  # the recognise may fail, so try 3 times
    #         try:
    #             text = self._img_to_word(name)
    #             if not text:
    #                 sleep(1)
    #                 continue
    #             return text
    #         except:
    #             sleep(1)
    #     return ''

    # def find(self, pics, threshold=0.95, timeout=1):
    #     """find the pictures.

    #     if any picture found, return its name and position
    #     if timeout, return None
    #     """
    #     for i in range(timeout):
    #         self._screenshot()
    #         img_rgb = cv2.imread(self.screenshots)
    #         img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    #         self.pic_bg = img_gray
    #         for pic in pics:
    #             pos = self._find_pic(pic, threshold)
    #             if pos:
    #                 print("find ", pic, "at ", pos)
    #                 logging.info('find {0} at {1}'.format(pic, pos))
    #                 return (pic, pos)
    #         sleep(0.7)
    #     print("timeout, find nothing.")
    #     logging.info("timeout, find nothing.")
    #     return None

    # def monitor(self, input, output):
    #     """
    #     used to monitor the game status
    #     """
    #     logging.info("monitor start.")

    #     try:
    #         for item in iter(input.get, 'STOP'):
    #             logging.info('Monitor: {}'.format(item))
    #             pics = item[0]
    #             threshold = item[1]
    #             timeout = item[2]
    #             #print('start to monitor', pics)
    #             res = self.find(pics, threshold, timeout)
    #             if res:
    #                 output.put(res)
    #             else:
    #                 output.put(('TIMEOUT', (-1,-1)))
    #         print('Monitor stoped by game event')
    #         logging.info('Monitor stoped by game event')
    #         output.put('STOP')
    #     except KeyboardInterrupt:
    #         print('Monitor stoped by user')
    #         logging.info('Monitor stoped by user')

    #     return None


if __name__ == '__main__':
    eye = Eye()
    pos_list = [
        (3, 3),
        (1, 3),
        (9, 9),
        (10, 11),
        (9, 20),
        (99, 21),
        (99, 100),
        (2, 2),
    ]
    print(eye.de_duplication(pos_list))