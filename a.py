#################################################
# 用于原型尝试
#
#############################################  

import pytesseract
from PIL import Image

f = 'b.jpg'
img = Image.open(f)
res = pytesseract.image_to_string(img, lang='chi_sim')
print(res)
