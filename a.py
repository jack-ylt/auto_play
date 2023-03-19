# 用于原型尝试
import pytesseract
from PIL import Image

for i in range(2, 8):
    print(i)
    text = pytesseract.image_to_string(Image.open(f"text{i}.jpg"))
    print(text)
    print('')
