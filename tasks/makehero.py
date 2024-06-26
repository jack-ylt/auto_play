import asyncio
import os
import sys
import re
from lib.global_vals import *
from tasks.task import Task
from lib.helper import main_dir


sys.path.insert(0, main_dir)
PIC_DIR = os.path.join(main_dir, 'pics')
SI_XI_ZHEN_YING = ['sh', 'zx', 'hd', 'xe']
GUANG_AN_ZHEN_YING = ['cz', 'hm']


class MakeHero(Task):
    """做狗粮英雄"""

    def __init__(self, player, role_setting, counter):
        super().__init__(player, role_setting, counter)
        self._all_heroes = []
        self.global_exclude = set()

    async def run(self):
        if not self.test():
            return

        await self.make_13x_heroes()

    def test(self):
        return True

    async def make_5x_heroes(self, zhen_ying='si_xi'):
        while True:
            num = await self.get_free_space()
            self.logger.info(f"free space: {num}")
            if num < 48:
                self.logger.info(f'break, free space is lettle (<48)')
                break

            success = await self.get_5x_cai_liao(num, zhen_ying)
            if not success:
                self.logger.info(f'break, 3星狗粮没有了')
                break

            # 合成5x
            success = await self.kuai_su_he_cheng()
            if not success:
                # 可能狗粮错配，需要clear_hero_space清理多余的4x、3x狗粮
                self.logger.info(f'break, 3星、4星狗粮不配对')
                break

        # 邀请一些9星潜力的英雄
        if zhen_ying == 'si_xi':
            await self.yao_qing_gouliang_5x(10)

    async def make_6x_heroes(self, zhen_yings=SI_XI_ZHEN_YING):
        await self.gamer.goto_main_ui()
        await self._move_to_left_top()
        await self.click('gai_zao_ying_xiong')
        await self.find('kuai_su_gai_zao')

        num_6x = 0

        if not isinstance(zhen_yings, list):
            zhen_yings = [zhen_yings]
        for zhen_ying in zhen_yings:
            try:
                await self.click(f"{zhen_ying}_gz", timeout=1)
            except FindTimeout:
                continue

            bentis_5x = self.hero_selector(zhen_ying, '5x', gou_liang='9x')
            gou_liang_5x = self.hero_selector(zhen_ying, '5x', gou_liang='6x')
            exclude_ids = set()
            pos_list = await self.find_all("red_point4", threshold=0.75)
            pos_list = [i for i in pos_list if i[1] > 360]
            for pos in pos_list:
                await asyncio.sleep(1)
                await self.click((pos[0]-20, pos[1]+20))

                try:
                    name, _ = await self.find(bentis_5x, timeout=2)
                    exclude_ids.add(name.split('_')[1])
                except FindTimeout:
                    # 不是狗粮，不合成(避免消耗最新的英雄)
                    continue

                if self.exist('0_ben_ti'):
                    # 本体不足，不合成
                    continue

                try:
                    await self.click((674, 238))
                    await self.select_gou_liang(gou_liang_5x, 1, excludes=exclude_ids)

                    await self.find('gai_zao1')
                    await self.click((674, 330))
                    await self.select_gou_liang(gou_liang_5x, 3, excludes=exclude_ids)
                    await self.click('gai_zao1')
                    await self.click(OK_BUTTONS)
                    await self.click(OK_BUTTONS)
                except NoEnoughGouLiang:
                    # 狗粮不足，直接看下一阵营
                    break

                await self.find('gai_zao1')

                num_6x += 1

        return num_6x

    async def make_6x_hero(self, zhen_ying, heroid):
        """用于合成特定6x英雄"""
        await self.gamer.goto_main_ui()
        await self._move_to_left_top()
        await self.click('gai_zao_ying_xiong')
        await self.find('kuai_su_gai_zao')

        benti_6x = f"{zhen_ying}_{heroid}_2face_ss"
        gou_liang_5x = self.hero_selector(zhen_ying, '5x', gou_liang='6x')

        await self.click(benti_6x)
        try:
            await self.click((674, 238))
            await self.select_gou_liang(gou_liang_5x, 1)

            await self.find('gai_zao1')
            await self.click((674, 330))
            await self.select_gou_liang(gou_liang_5x, 3)
            await self.click('gai_zao1')
            await self.click(OK_BUTTONS)
            await self.click(OK_BUTTONS)
        except NoEnoughGouLiang:
            return False

        return True

    async def make_9x_heroes(self, zhen_yings=SI_XI_ZHEN_YING):
        await self.gamer.goto_main_ui()
        await self.click('ying_xiong')
        num_9x = 0

        if not isinstance(zhen_yings, list):
            zhen_yings = [zhen_yings]

        for zhen_ying in zhen_yings:
            self.logger.info(f"make 9x heroes for {zhen_ying}")
            await self.click(f"{zhen_ying}_L")

            heroes_6x = set()
            heroes_5x = set()
            names_6x = self.hero_selector(zhen_ying, '6x')
            names_5x = self.hero_selector(zhen_ying, '5x')
            num_6x = 0
            while True:
                if self.exist('6x', threshold=0.9):
                    found = await self.player.find_all_name(names_6x, threshold=0.9)
                    heroes_6x.update(set(found))
                if self.exist('5x', threshold=0.9):
                    found = await self.player.find_all_name(names_5x, threshold=0.9)
                    heroes_5x.update(set(found))

                num = len(await self.find_all('6x', threshold=0.9))
                if num > num_6x:
                    num_6x = num
                    await self.swipe_up('ying_xiong_tong_ji')
                else:
                    break

            if num_6x < 4:
                self.logger.info(f"skip, no enough 6x heroes ({num_6x} < 4)")
                continue

            id_10x = set([i.split('_')[1]
                         for i in self.hero_selector(zhen_ying, '10x')])
            id_5x = set([i.split('_')[1] for i in heroes_5x])
            id_9x = id_10x & id_5x

            heroes_to_9x = []

            for hero in heroes_6x:
                num = hero.split('_')[1]
                if num in id_9x:
                    heroes_to_9x.append(hero)

            if not heroes_to_9x:
                self.logger.info("skip, no hero can trun to be 9x)")
                continue

            # 滑到顶部（一般8x肯定都在第一页）
            while True:
                if await self.swipe_down(mode='ying_xiong_tong_ji'):
                    break

            hero_6x = heroes_to_9x[0]
            num = hero_6x.split('_')[1]
            exclude_ids = set([num])    # 避免把自己的5x本体吃掉

            await self.click(hero_6x)

            # 升100级
            name, _ = await self.find(['jin_jie', 'jue_xing'])
            if name == 'jin_jie':
                pos_upgrade = (825, 365)
                for i in range(6):
                    await self.find('sheng_ji')
                    await self.click(pos_upgrade)
                    await self.click(OK_BUTTONS)
                    await self.click('jin_jie')
                    await self.click('jin_jie1')

            # 觉醒到7星
            gou_liang_5x = self.hero_selector(zhen_ying, '5x')
            gou_liang_6x = self.hero_selector(zhen_ying, '6x')
            await self.click('jue_xing')
            await self.click('5x1')
            await self.select_gou_liang_5x(gou_liang_5x, 4, excludes=exclude_ids)
            await self.click('jue_xing1')
            await self.click(OK_BUTTONS)

            # 觉醒到8星
            await self.click('jue_xing')
            await self.click('6x1')
            await self.select_gou_liang_5x(gou_liang_6x, 1)    # 6x不必担心本体被误吃
            await self.click('5x1')
            await self.select_gou_liang_5x(gou_liang_5x, 3, excludes=exclude_ids)
            await self.click('jue_xing1')
            await self.click(OK_BUTTONS)

            # 觉醒到9星
            await self.click('jue_xing')
            hero_5x = hero_6x.replace('6x', '5x')
            await self.click(hero_5x)
            await self.select_gou_liang_5x(hero_5x, 1)
            await self.click('6x1')
            await self.select_gou_liang_5x(gou_liang_6x, 1)
            await self.click('5x1')
            await self.select_gou_liang_5x(gou_liang_5x, 2, excludes=exclude_ids)
            await self.click('jue_xing1')
            await self.click(OK_BUTTONS)

            await self.player.go_back()
            num_9x += 1

        return num_9x

    async def make_13x_heroes(self):
        developing_heroes = await self.get_developing_heroes()
        if not developing_heroes:
            self.logger.info("Skip, no developing_heroes need to be made")
            return

        await self.clear_hero_space()

        for zhen_ying in SI_XI_ZHEN_YING:
            benti_list = [
                i for i in developing_heroes if i.startswith(zhen_ying)]
            benti_ids = [i.split('_')[1] for i in benti_list]
            self.global_exclude = set(benti_ids)
            for heroid in benti_ids:
                if not await self.prepare_9x_gouliang(require=3):
                    self.logger.warning(f"9星狗粮不足(不足3)")
                    return

                if not await self.prepare_6x_gouliang(zhen_ying, require=5):
                    self.logger.warning(f"6星狗粮不足(不足5)")
                    return

                if not await self.prepare_benti(zhen_ying, heroid, require=7):
                    self.logger.warning(f"本体不足(不足7)")
                    continue

                await self.make_13x_hero(zhen_ying, heroid)

    async def make_13x_hero(self, zhen_ying, heroid):
        target = f"{zhen_ying}_{heroid}_2face_ss"
        benti_5x = f"{zhen_ying}_{heroid}_5x"
        benti_6x = f"{zhen_ying}_{heroid}_6x"
        gou_liang_5x = self.hero_selector(zhen_ying, '5x', gou_liang='9x')

        # 6星
        await self.gamer.goto_main_ui()
        await self._move_to_left_top()
        await self.click('gai_zao_ying_xiong')
        await self.find('kuai_su_gai_zao')
        await self.click(target)
        await self.find(benti_5x)
        await self.click((674, 238))
        await self.select_gou_liang(gou_liang_5x, 1)
        await self.find('gai_zao1')
        await self.click((674, 330))
        await self.select_gou_liang(gou_liang_5x, 3)
        await self.click('gai_zao1')
        await self.click(OK_BUTTONS)
        await self.click(OK_BUTTONS)

        # 100级
        await self.gamer.goto_main_ui()
        await self.click('ying_xiong')
        await self.click(zhen_ying)
        await self.click(benti_6x, timeout=2)

        name, _ = await self.find(['jin_jie', 'jue_xing'])
        if name == 'jin_jie':
            pos_upgrade = (825, 365)
            for i in range(6):
                await self.find('sheng_ji')
                await self.click(pos_upgrade)
                await self.click(OK_BUTTONS)
                await self.click('jin_jie')
                await self.click('jin_jie1')

        # 觉醒到7星
        gou_liang_6x = self.hero_selector(zhen_ying, '6x')
        await self.click('jin_jie')
        await self.click('jin_jie1')
        await self.click('jue_xing')
        await self.click('5x1')
        await self.select_gou_liang_5x(gou_liang_5x, 4)
        await self.click('jue_xing1')
        await self.click(OK_BUTTONS)

        # 觉醒到8星
        await self.click('jue_xing')
        await self.click('6x1')
        await self.select_gou_liang_5x(gou_liang_6x, 1)    # 6x不必担心本体被误吃
        await self.click('5x1')
        await self.select_gou_liang_5x(gou_liang_5x, 3)
        await self.click('jue_xing1')
        await self.click(OK_BUTTONS)

        # 觉醒到9星
        await self.click('jue_xing')
        await self.click(benti_5x)
        await self.select_gou_liang_5x(benti_5x, 1)
        await self.click('6x1')
        await self.select_gou_liang_5x(gou_liang_6x, 1)
        await self.click('5x1')
        await self.select_gou_liang_5x(gou_liang_5x, 2)
        await self.click('jue_xing1')
        await self.click(OK_BUTTONS)

        # 10星
        gou_liang_9x = self.hero_selector(SI_XI_ZHEN_YING, '2face')
        await self.click('jue_xing')
        await self.click(benti_5x)
        await self.select_gou_liang_5x(benti_5x, 2)
        await self.click('9x1')
        await self.select_gou_liang_5x(gou_liang_9x, 1)
        await self.click('6x1')
        await self.select_gou_liang_5x(gou_liang_6x, 1)
        await self.click('jue_xing1')
        await self.click(OK_BUTTONS)

        # 11星
        await self.click('ji_ying_jin_hua')
        await self.click('9x1')
        await self.select_gou_liang_5x(gou_liang_9x, 1)
        await self.click('ji_ying_jin_hua1.jpg')
        await self.click(OK_BUTTONS)

        # 12星
        await self.click('ji_ying_jin_hua')
        await self.click(benti_5x)
        await self.select_gou_liang_5x(benti_5x, 1)
        await self.click('9x1')
        await self.select_gou_liang_5x(gou_liang_9x, 1)
        await self.click('ji_ying_jin_hua1.jpg')
        await self.click(OK_BUTTONS)

        # 13星
        await self.click('ji_ying_jin_hua')
        await self.click(benti_5x)
        await self.select_gou_liang_5x(benti_5x, 1)
        await self.click('9x1')
        await self.select_gou_liang_5x(gou_liang_9x, 1)
        await self.click('ji_ying_jin_hua1.jpg')
        await self.click(OK_BUTTONS)

    async def prepare_benti(self, zhen_ying, heroid, require=7):
        await self.gamer.goto_main_ui()
        await self._move_to_left_top()
        await self.click('gai_zao_ying_xiong')
        await self.find('kuai_su_gai_zao')

        benti_6x = f"{zhen_ying}_{heroid}_2face_ss"
        benti_5x = f"{zhen_ying}_{heroid}_5x"

        await self.click(benti_6x)
        await self.click((165, 240))
        num1 = len(await self.find_all('5x'))
        if num1 >= require:
            return True

        await self.click('he_cheng_s')
        try:
            await self.click(benti_5x, timeout=2)
        except FindTimeout:
            return False

        num2 = await self.player.get_sui_pian_num((430, 295))
        if num1 + num2 >= require:
            await self.click('he_cheng')
            await self.click(OK_BUTTONS)
            return True
        return False

    async def prepare_9x_gouliang(self, require=3):
        old_9x = await self.count_9x_gouliang()
        if old_9x > require:
            self.logger.info(f"Skip, old_9x is: {old_9x} (> {require})")
            return True

        await self.make_5x_heroes()
        await self.make_6x_heroes()
        await self.make_5x_heroes()
        new_9x = await self.make_9x_heroes()
        total_9x = old_9x + new_9x
        if total_9x >= require:
            return True

        for zhen_ying in SI_XI_ZHEN_YING:
            await self.make_5x_heroes(zhen_ying)
            await self.make_6x_heroes(zhen_ying)
            await self.make_5x_heroes(zhen_ying)
            num = await self.make_9x_heroes(zhen_ying)
            total_9x += num
            if total_9x >= require:
                return True
        return False

    async def count_9x_gouliang(self):
        await self.gamer.goto_main_ui()
        await self.click('ying_xiong')
        await self.find('sh_L')
        num_9x = 0
        while True:
            if self.exist('9x'):
                pos_list = await self.find_all(self.hero_selector(SI_XI_ZHEN_YING, '9x'))
                num_9x += len(pos_list)

            if self.exist(['6x', '5x', '4x', '3x']):
                break
            else:
                res = await self.swipe_up('ying_xiong_tong_ji')
                if res == 'reach_down':
                    break
        return num_9x

    async def prepare_6x_gouliang(self, zhen_ying, require=5):
        old_6x = await self.count_6x_gouliang(zhen_ying)
        if old_6x > require:
            self.logger.info(f"Skip, old_6x is: {old_6x} (> {require})")
            return True

        await self.make_5x_heroes(zhen_ying)
        new_6x = await self.make_6x_heroes(zhen_ying)
        await self.make_5x_heroes(zhen_ying)

        if old_6x + new_6x >= require:
            return True
        else:
            return False

    async def count_6x_gouliang(self, zhen_ying):
        await self.gamer.goto_main_ui()
        await self.click('ying_xiong')
        await self.click(f'{zhen_ying}_L')
        num_6x = 0
        while True:
            if self.exist('6x'):
                pos_list = await self.find_all(self.hero_selector(zhen_ying, '6x'))
                num_6x += len(pos_list)

            if self.exist(['5x', '4x', '3x']):
                break
            else:
                res = await self.swipe_up('ying_xiong_tong_ji')
                if res == 'reach_down':
                    break
        return num_6x

    async def get_developing_heroes(self):
        await self._move_to_center()
        await self.click('ying_xiong_ji_di')
        await self.click('xin_pian_ri_zhi')

        heroes = []
        for zhen_ying in SI_XI_ZHEN_YING:
            await self.click(f"{zhen_ying}_L")
            await asyncio.sleep(1)
            # TODO 这个6x可能无匹配，需要叠加xing
            hero_names = self.hero_selector(
                zhen_ying, ['5x', '6x', '10x'], scene='xin_pian_ri_zhi')
            xing_names = ['5x_s', '6x_s', '9x_s', '10x_s']
            found_names = await self.player.find_combo(hero_names, xing_names, dx=(-20, 20), dy=(-40, -10))
            heroes.extend(found_names)
            # print(found_names)

        return heroes

    def hero_selector(self, zhen_ying, xing, scene='hero', gou_liang='9x'):
        if not isinstance(zhen_ying, list):
            zhen_ying = [zhen_ying]
        if not isinstance(xing, list):
            xing = [xing]

        heroes = []
        for i in self.get_all_heroes():
            zy, num, x = i.split('_')[0:3]
            if zy in zhen_ying and x in xing:
                heroes.append(i)

        if scene == "hero":
            heroes = [i for i in heroes if len(i.split('_')) == 3]
        elif scene == 'gai_zao':
            heroes = [i for i in heroes if i.endswith('_ss')]
        elif scene == 'xin_pian_ri_zhi':
            heroes = [i for i in heroes if i.endswith('_s')]
        elif scene == 'all':
            pass
        else:
            raise InternalError(f"Unknown scene: {scene}")

        if gou_liang == '6x':
            heroes = [i for i in heroes if int(i.split('_')[1]) <= 10]
        elif gou_liang == '9x':
            heroes = [i for i in heroes if int(i.split('_')[1]) <= 25]
        elif gou_liang == 'all':
            pass
        else:
            raise InternalError(f"Unknown cai_liao: {gou_liang}")

        return heroes

    def get_all_heroes(self):
        if self._all_heroes:
            return self._all_heroes

        hero_dir = os.path.join(PIC_DIR, 'heroes')
        heroes = []

        # 阵营_序号_星级
        for root, dirs, files in os.walk(hero_dir):
            for f in files:
                f_name = os.path.splitext(f)[0]
                tokens = f_name.split('_')
                if len(tokens) >= 3:
                    heroes.append(f_name)

        return heroes

    async def clear_hero_space(self):
        await self.kuai_su_he_cheng()
        await self.dismiss_heroes()
        await self.clear_3x_4x()

    async def clear_3x_4x(self, zhen_yings=SI_XI_ZHEN_YING + GUANG_AN_ZHEN_YING):
        if not zhen_yings:
            return

        await self.gamer.goto_main_ui()
        await self.click('ying_xiong')

        while zhen_yings:
            zhen_ying = zhen_yings.pop(0)
            await self.click(f'{zhen_ying}_L')
            n3, n4 = await self.get_3x_4x_num()
            if n3 > 7:
                num = n3 * 2 - n4
                await self.yao_qing_cai_liao(zhen_ying, '4x', num)
                await self.kuai_su_he_cheng()
                break
            elif n4 > 15:
                num = n4 // 2 - n3
                await self.yao_qing_cai_liao(zhen_ying, '3x', num)
                await self.kuai_su_he_cheng()
                break
            else:
                continue

        await self.clear_3x_4x(zhen_yings)

    async def get_3x_4x_num(self):
        await self.swipe_up(mode='ying_xiong_tong_ji')
        num_3x = len(await self.find_all(['3x', '3x1'], threshold=0.85))
        num_4x = len(await self.find_all(['4x', '4x1'], threshold=0.85))
        return num_3x, num_4x

    async def dismiss_heroes(self):
        await self.gamer.goto_main_ui()
        await self._move_to_left_top()
        await self.click('qian_san_ying_xiong')

        end = False
        while not end:
            await self.find('ying_xiong_shu_liang')
            if not self.exist(['1x', '2x'], threshold=0.9):
                break
            if self.exist(['3x', '4x', '5x', 'hm', 'cz'], threshold=0.9):
                await self.click('1xing')
                await self.click('quick_put_in')
                await self.click('2xing')
                await self.click('quick_put_in')
                end = True
            else:
                await self.player.find_then_click('quick_put_in')

            await self.player.find_then_click('dismiss')
            name, _ = await self.find(['ok8', 'receive1'])
            if name == 'ok8':
                await self.click('ok8')
            await self.player.find_then_click('receive1')

    async def select_gou_liang(self, gou_liang, wanted=1, excludes=None):
        await self.find('xuan_zhong')
        num = 0
        reach_down = False

        if excludes:
            heroes = []
            for i in gou_liang:
                _, id, _ = i.split('_')
                if not id in excludes:
                    heroes.append(i)
        else:
            heroes = gou_liang[:]

        while num < wanted:
            pos_list = await self.find_all(heroes, threshold=0.85)
            # 排好序，选择起来就不会看起来乱
            pos_list.sort(key=lambda x: (round(x[1] / 10), x[0]))
            for pos in pos_list[:wanted]:
                await self.click(pos)
                num += 1

            if num < wanted:
                if reach_down or self.exist('reach_down'):
                    break
                else:
                    reach_down = await self.swipe_up()

        await self.click('xuan_zhong')

        if num < wanted:
            raise NoEnoughGouLiang()

    async def select_gou_liang_5x(self, gou_liang, wanted=1, excludes=None):
        await self.find('fang_ru')
        num = 0
        reach_down = False

        if not isinstance(gou_liang, list):
            gou_liang = [gou_liang]

        exclude_ids = set()
        # exclude_ids.update(self.global_exclude)
        if excludes:
            exclude_ids.update(excludes)

        if exclude_ids:
            heroes = []
            for i in gou_liang:
                _, id, _ = i.split('_')
                if not id in exclude_ids:
                    heroes.append(i)
        else:
            heroes = gou_liang[:]

        while num < wanted:
            pos_list = await self.find_all(heroes, threshold=0.9)
            pos_list.sort(key=lambda x: (round(x[1] / 10), x[0]))
            for pos in pos_list[:wanted]:
                await self.click(pos)
                num += 1

            if num < wanted:
                if reach_down or self.exist('reach_down'):
                    break
                else:
                    reach_down = await self.swipe_up()

        await self.click('que_ding1')

        if num < wanted:
            raise NoEnoughGouLiang()

    async def yao_qing_gouliang_5x(self, num):
        await self.gamer.goto_main_ui()

        await self.click('bei_bao_2')
        await self.click('sui_pian_icon')
        await self.click('si_xi_m')
        await self.click('5x1')
        try:
            await self.click('yao_qing', timeout=3)
        except FindTimeout:
            # 狗粮不足1个
            return
        await self.find('jia')
        input_pos = (430, 295)
        await self.player.information_input(input_pos, str(num))
        await self.click(['que_ding', 'que_ding_L'])
        # 数字识别可能失败，比如44无法识别
        await self.click('he_cheng')
        await self.click(OK_BUTTONS)

    async def kuai_su_he_cheng(self):
        await self.gamer.goto_main_ui()
        await self._move_to_left_top()
        await self.click('gai_zao_ying_xiong')
        await self.click('kuai_su_gai_zao')

        success = False

        # 合成5星狗粮
        await self.click('5xing_gai_zao')
        await asyncio.sleep(1)
        await self.click('gai_zao')
        if not self.player.is_exist('mei_you_ke_gai'):
            await self.click(OK_BUTTONS)
            success = True

        # 合成4星狗粮
        await self.click('4xing_gai_zao')
        await asyncio.sleep(1)
        await self.click('gai_zao')
        if not self.player.is_exist('mei_you_ke_gai'):
            await self.click(OK_BUTTONS)
            success = True

        return success

    async def get_hero_num(self, xing_pos):
        """获取碎片数量，得到英雄数量"""
        x, y = xing_pos
        area = (x-32, y+8, x+32, y+20)
        print('area', area)
        text = self.player.get_text(area)
        text = re.sub(r'[^0123456789/]', ' ', text)
        try:
            n1, n2 = text.split('/')
            return int(n1) // int(n2)
        except Exception:
            await self.click((x, y-30))
            try:
                # 不足一个，就不会弹出邀请按钮
                await self.click('yao_qing', timeout=2)
            except FindTimeout:
                await self.click((120, 460))
                return 0
            await self.find('jia')
            # text = self.player.get_text((400, 282, 480, 306))
            # text = re.sub(r'[^0123456789]', ' ', text)
            num = await self.player.get_sui_pian_num((430, 295))
            # 关掉弹出的窗口
            await self.click((120, 460))
            await self.click((120, 460))
            return num

    async def get_5x_cai_liao(self, num, zhen_ying='si_xi'):
        await self.gamer.goto_main_ui()
        await self.click('bei_bao_2')
        await self.click('sui_pian_icon')
        await self.click(f"{zhen_ying}_m")
        await asyncio.sleep(1)

        if await self.no_cai_liao('3x'):
            return False
        elif await self.no_cai_liao('4x'):
            await self.yao_qing('3x', num)
            return True
        else:
            n = int(num // 3)
            await self.yao_qing('3x', n)
            await self.yao_qing('4x', 2 * n)
            return True

    async def yao_qing_cai_liao(self, zhen_ying, xing, num):
        await self.gamer.goto_main_ui()
        await self.click('bei_bao_2')
        await self.click('sui_pian_icon')
        await self.click(f"{zhen_ying}_m")
        await asyncio.sleep(1)
        await self.yao_qing(xing, num)

    async def yao_qing(self, xing, num):
        xing = [xing, f"{xing}1"]
        rest = num
        for pos in await self.find_all(xing, threshold=0.85):
            await asyncio.sleep(1)
            n = await self._do_yao_qing((pos[0], pos[1]-20), rest)
            rest -= n
            if rest <= 0:
                break

    async def no_cai_liao(self, xing):
        xing = [xing, f"{xing}1"]
        for pos in await self.find_all(xing, threshold=0.85):
            n = await self.get_hero_num(pos)
            if n is None:
                # 识别不成功，但一定是>0的
                return False
            elif n > 0:
                return False
        return True

    async def _do_yao_qing(self, hero_pos, num):
        await self.click(hero_pos)
        try:
            await self.click('yao_qing', timeout=2)
        except FindTimeout:
            await self.click((125, 460))
            return 0

        name, _ = await self.find(['he_cheng', 'ok9'])
        if name == 'he_cheng':
            input_pos = (430, 295)
            real_num = await self.player.set_sui_pian_num(input_pos, num)
            await self.click('he_cheng')
        else:
            real_num = 1

        await self.click(OK_BUTTONS)
        return real_num

    async def get_free_space(self):
        await self.gamer.goto_main_ui()
        await self.click('ying_xiong')
        await self.find('sh_L')
        area = (90, 105, 175, 128)
        text = self.player.get_text(area)
        try:
            used, total = text.split('/')
        except:
            raise TextRecognitionFailure()

        return int(total) - int(used)

    async def swipe_up(self, mode="xuan_gou_liang"):
        if mode == "xuan_gou_liang":
            p1 = (675, 380)
            p2 = (675, 150)
        elif mode == "ying_xiong_tong_ji":
            p1 = (745, 464)
            p2 = (745, 127)

        res = await self.drag_then_find(p1, p2, 'reach_down')
        if res:
            await asyncio.sleep(1)

        return res

    async def swipe_down(self, mode="xuan_gou_liang"):
        if mode == "xuan_gou_liang":
            p1 = (675, 160)
            p2 = (675, 390)
        elif mode == "ying_xiong_tong_ji":
            p1 = (745, 155)
            p2 = (745, 490)

        res = await self.drag_then_find(p1, p2, 'reach_top')
        if res:
            await asyncio.sleep(1)

        return res
