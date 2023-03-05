# 用于原型尝试

import os
import time
import subprocess
from playsound import playsound

app_dir = r'C:\Program Files\7-Zip'
app_name = '7z.exe'
app_path = os.path.join(app_dir, app_name)
zip_pwd = 'Qq8738091'


def do_zip(base_dir, name):
    print(f"zip {name} ...")
    src_path = os.path.join(base_dir, name)
    dest_path = os.path.join(base_dir, name + '.zip')
    cmd = [app_name, 'a', dest_path, '-p'+zip_pwd, '-y', src_path]

    res = subprocess.Popen(cmd, executable=app_path,
                           stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    res.wait()

def zip_for_each(base_dir):
    for i in os.listdir(base_dir):
        do_zip(base_dir, i)

if __name__ == "__main__":
    base_dir = r'E:\个人资料\zzt\2duu'
    zip_for_each(base_dir)
    playsound('./sounds/end.mp3')
