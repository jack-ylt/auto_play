#################################################
# 用于原型尝试
#
#############################################  

baick_dir = r'D:\Downloads\R1143《510L-580L》Dragon Masters 1-23 20册有音频\音频1-20'

# 遍历目录下的所有目录和文件
def get_all_files(dir):
    import os
    for root, dirs, files in os.walk(dir):
        father_dir = os.path.split(root)[1]
        if father_dir[0] in '012':
            print('father_dir:', father_dir)
            print('--------------------------------')
            pre = father_dir[0:3]

            # 重命名文件
            for file in files:
                if file.startswith(pre):
                    continue
                print('file:', file)
                os.rename(os.path.join(root, file), os.path.join(root, pre + file))

get_all_files(baick_dir)