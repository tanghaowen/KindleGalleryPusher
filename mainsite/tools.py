import hashlib, os, requests
from urllib.parse import urlsplit, parse_qs

from bs4 import BeautifulSoup


def hash_file(file_object):
    h = hashlib.sha1()
    chunk = 0
    while chunk != b'':
        chunk = file_object.read(1024)
        h.update(chunk)
    return h.hexdigest()


def get_hash_filename(file_object):
    file_object.seek(0)
    hash = hash_file(file_object)

    hash_file_name = hash[:2] + '/' + hash[2:4] + '/' + hash[4:]
    # 草泥马，出个bug，几本book封面图片怎么都加载不出来， 排查半天发现是/img/ad/的路径触发了广告屏蔽
    if 'ad/' in hash_file_name:
        hash_file_name = hash_file_name.replace('ad/', 'fuck/')
    return hash_file_name


if __name__ == '__main__':
    # テスト用
    pass
