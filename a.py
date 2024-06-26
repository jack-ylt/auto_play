#################################################
# 用于原型尝试
#
#############################################



import cv2
import numpy as np

# 读取图片，并转为灰度图
img1 = cv2.imread('./aaaa1.jpg')
img2 = cv2.imread('./aaaa2.jpg')
gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

# 创建orb对象
orb = cv2.ORB_create()
# 对ORB进行检测
kp1, dst1 = orb.detectAndCompute(gray1, None)
kp2, dst2 = orb.detectAndCompute(gray2, None)
# 判断描述子的数据类型，若不符合，则进行数据替换
if dst1.dtype != 'float32':
    dst1 = dst1.astype('float32')
if dst2.dtype != 'float32':
    dst2 = dst2.astype('float32')

# 创建匹配器(FLANN)
flann = cv2.FlannBasedMatcher()
# 描述子进行匹配计算
matches = flann.match(dst1, dst2)
img3 = cv2.drawMatches(img1, kp1, img2, kp2, matches, None)

cv2.imshow('img3', img3)

a = input("press any key to quit ...")