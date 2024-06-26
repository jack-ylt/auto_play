from PIL import Image

# 将图片转化为RGB
def make_regalur_image(img, size=(64, 64)):
    gray_image = img.resize(size).convert('RGB')
    return gray_image

# 计算直方图
def hist_similar(lh, rh):
    assert len(lh) == len(rh)
    hist = sum(1 - (0 if l == r else float(abs(l - r)) / max(l, r)) for l, r in zip(lh, rh)) / len(lh)
    return hist

# 计算相似度
def calc_similar(li, ri):
    calc_sim = hist_similar(li.histogram(), ri.histogram())
    return calc_sim

if __name__ == '__main__':
    image_cp1 = Image.open('1.jpg')
    image_cp1 = make_regalur_image(image_cp1)
    image_cp2 = Image.open('4.jpg')
    image_cp2 = make_regalur_image(image_cp2)
    print("图片间的相似度为", calc_similar(image_cp1, image_cp2))