from PIL import Image
from io import BytesIO


def saveImageToSpecificSizeJpeg(image_path, jpeg_size_limit):
    image = Image.open(image_path)  # type:Image.Image

    for quality in range(80, 9, -5):
        print("Try quality %d ..." % quality)
        tmp_memo_area = BytesIO()
        image.save(tmp_memo_area, "jpeg", quality=quality, optimize=True, progressive=True)
        jpeg_size = tmp_memo_area.__sizeof__() / 1024.0
        print("jpeg size is %.1fKB/.2f%fKB" % (jpeg_size, jpeg_size_limit))
        if jpeg_size < jpeg_size_limit:
            print("OK! save jpeg with quality %d" % quality)
            image.save(image_path, quality=quality, optimize=True, progressive=True)
            break
    image.close()


saveImageToSpecificSizeJpeg("test.jpg", 200)
