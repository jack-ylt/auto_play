# 地图上的point，不一定最右边的就是最新的，有一两个是往上拐的
# =》 按照距离最近的原则，串成一条线？
# 串成一小段、一小段，然后以平均x来排序，取x大的那条
# 再更具倒数第二条，确定头尾，再根据头尾的走势，决定点哪里

# import math
# import sys

# # pos_list1 = [(159, 358), (594, 138), (638, 143), (557, 159), (722, 186), (535, 191), (29, 287), (382, 296), (55, 311), (696, 313),
# #              (371, 329), (725, 337), (766, 339), (352, 354), (806, 358), (324, 381), (683, 163), (706, 259), (689, 282), (93, 322)]

# pos_list1 = [(445, 339), (317, 143), (236, 159), (401, 186), (214, 191), (805, 237), (805, 274), (61, 296), (826, 311), (375, 313), (50, 329),
#              (404, 337), (31, 354), (485, 358), (837, 403), (675, 407), (784, 413), (728, 416), (273, 137), (362, 163), (385, 259), (368, 282), (854, 335)]

# max_dis = 60

# def distance(p1, p2):
#     x = (p1[0] - p2[0]) ** 2
#     y = (p1[1] - p2[1]) ** 2
#     dist = math.sqrt(x + y)
#     return dist

# print(distance(  (784, 413), (837, 403)   ))

# # sys.exit()

# def get_segment(pos, pos_list, segment, forward=True):
#     min_d = 100
#     min_p = None
#     for p in pos_list:
#         d = distance(p, pos)
#         if d < min_d:
#             min_d = d
#             min_p = p

#     if min_d < max_dis:
#         if forward:
#             segment.append(min_p)
#         else:
#             segment.insert(0, min_p)
#         pos_list.remove(min_p)
#         return get_segment(min_p, pos_list, segment)
#     else:
#         return pos_list

# # lst = []
# # for i in pos_list1:
# #     min_v = 100
# #     for j in pos_list1:
# #         if i != j:
# #             d = distance(i, j)
# #             if d < min_v:
# #                 min_v = d
# #     # print(min)
# #     lst.append(min_v)
# # lst.sort()
# # print(lst[:5], lst[-5:])
# # print(min(lst), sum(lst)/len(lst), max(lst))


# pos_list = pos_list1[:]
# pos_list.sort()
# segment_list = []

# while pos_list:
#     pos = pos_list[0]
#     segment = [pos]
#     pos_list = get_segment(pos, pos_list[1:], segment)
#     # 看另一个方向是否还有
#     pos_list = get_segment(segment[0], pos_list, segment, forward=False)
#     segment_list.append(segment)
#     print(segment)
# # print(segment_list)

# max_avg_x = 0
# res = None
# for segment in segment_list:
#     avg_x = sum(map(lambda x: x[0], segment)) / len(segment)
#     # print(avg_x, segment)
#     if avg_x > max_avg_x:
#         max_avg_x = avg_x
#         res = segment

# print(max_avg_x, res)


# # print(distance((661, 259), (677, 186)))
