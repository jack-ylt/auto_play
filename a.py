# 用于原型尝试

import pytesseract
from PIL import Image


if __name__ == '__main__':
    img = Image.open('text2.jpg')
    config = r'--oem 3 --psm 7 outputbase digits'
    # comfig = r'-c tessedit_char_whitelist=0123456789 --psm 6'
    # text = pytesseract.image_to_string(img, config=config)
    text = pytesseract.image_to_string(img)
    print(repr(text))
    print(text)

