# -*-coding:utf-8-*-

from aip import AipOcr
# from ..configs.aip_config import config
config = {
    'appId': '14224264',
    'apiKey': 'acb29MRO413yLSuTkC2TIfXd',
    'secretKey': '2abIQ9DTiBaZTK1FrKx1OqGzIbT2pVGW'}

import logging
logger = logging.getLogger(__name__)

client = AipOcr(**config)

options = {}
options["language_type"] = "ENG"
options["probability"] = "true"


def get_file_content(file_path):
    with open(file_path, 'rb') as fp:
        return fp.read()


def get_texts(file_path, options=options):
    image = get_file_content(file_path)
    texts = client.basicGeneral(image, options)
    return texts


def find_text_pos(file_path, text, options=options):
    """return a pos, or (-1, -1)"""
    image = get_file_content(file_path)
    text_dict = client.general(image, options)
    words_result = text_dict.get('words_result', [])
    # for w in words_result:
    #     print(w)

    for i in words_result:
        words = i['words']
        if text in words:
            logger.debug(str(i))
            loc = i['location']
            x = int(loc['left'] + (loc['width'] / 2))
            y = int(loc['top'] + (loc['height'] / 2))
            return (x, y)

    return (-1, -1)

if __name__ == '__main__':
    # image = get_file_content('a.jpg')
    # text_dict = client.general(image, options)
    # words_result = text_dict.get('words_result', [])
    # print(words_result)
    import pytesseract
    import cv2

    def test_text(image_file):

        return tesseract.image_to_string(
                Image.open(image_file),
                lang=lang,
                builder=tesseract.DigitBuilder())

    image_file = 'a.jpg'

    test_text(image_file)
