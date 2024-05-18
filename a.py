#################################################
# 用于原型尝试
#
#############################################

import cv2
import os
import re
from PIL import Image


def get_video_size(fpath):
    video = cv2.VideoCapture(fpath)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    return width, height


def get_image_size(fpath):
    size = Image.open(fpath).size
    return size


def simplify_name(fanme):
    s1 = r"幼女萝莉资源luolihao.com打不开请开VPN-"
    res = fanme.replace(s1, '')
    for s in "- _()":
        res = res.replace(s, '')
    return res


def main():
    # base_dir = r"E:\资料\zz\xiaoma2"
    base_dir = r'E:\资料\zz\ztmv'
    image_num = 0
    video_num = 0

    for root, dnames, fnames in os.walk(base_dir):
        for f in fnames:
            new_f = f
            # 已经加了分辨率了，不重复加
            if re.match(r'\d+x\d+_', f):
                continue

            # # 已经有分辨率了，删除分辨率
            # if re.match(r'\d+x\d+_', f):
            #     new_f = re.sub(r'\d+x\d+_', '', new_f)

            new_f = simplify_name(new_f)

            # 添加分辨率前缀
            if f.endswith('.jpg'):
                image_num += 1
                try:
                    w, h = get_image_size(os.path.join(root, f))
                    new_f = f"{min(w,h)}x{max(w,h)}_{new_f}"
                except Exception:
                    pass
            elif f.endswith('.txt'):
                pass
            else:
                # 视频格式太多了
                video_num += 1
                try:
                    w, h = get_video_size(os.path.join(root, f))
                    new_f = f"{min(w,h)}x{max(w,h)}_{new_f}"
                except Exception:
                    pass


            # 重命名
            os.rename(os.path.join(root, f), os.path.join(root, new_f))

    print(f"image_num: {image_num}, video_num: {video_num}")

main()


# TODO 出了个bug，就是已经简化了，重复简化；已经加了前缀，重复加前缀
