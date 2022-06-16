

import os

from numpy import full

from lib import emulator

def findfile(start, name):
    for path, dirs, files in os.walk(start):
        if name in files:
            full_path = os.path.join(start, path, name)
            full_path = os.path.normpath(os.path.abspath(full_path))
            return full_path

# start = r'D:\Program Files'
start = r'D:\\'
name = 'MultiPlayerManager.exe'
print('start')
emulator_file = findfile(start, name)
os.startfile(emulator_file)
print('end')

