import hashlib,os,requests
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

    hash_file_name = hash[:2] +'/'+ hash[2:4] +'/'+ hash[4:]
    # 草泥马，出个bug，几本book封面图片怎么都加载不出来， 排查半天发现是/img/ad/的路径触发了广告屏蔽
    if 'ad/' in hash_file_name:
        hash_file_name = hash_file_name.replace('ad/','fuck/')
    return hash_file_name


class BookInfoSpider:
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0",
               "Accept-Language":"zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2"}
    bangumi_host = 'bgm.tv'
    mediaarts_host = 'mediaarts-db.bunka.go.jp'
    sakuhindb_host = 'sakuhindb.com'
    mangazenkan = 'www.mangazenkan.com'

    def __init__(self):
        self.session = requests.Session()

    def get(self,full_url,headers,stream=False):
        if stream :
            response = self.session.get(full_url, headers=headers, stream=True)
        else:
            response = self.session.get(full_url,headers=headers)
        return response

    def get_book_info_from_bangumi(self,book_id):
        if isinstance(book_id,int):
            book_id = str(book_id)
        title = ""
        title_chinese = ""
        author = []
        desc = ""
        tags = []
        covers = []
        full_url = "https://%s/subject/%s" % (self.bangumi_host,book_id)
        append_headers = {"Referer":"https://"+self.bangumi_host,"Host":self.bangumi_host}
        response = self.get(full_url,{**append_headers,**self.headers})
        response_text = response.content.decode("utf-8")
        html = BeautifulSoup(response_text,features="lxml")

        title = html.select(".nameSingle > a")[0].string
        detail_box_doms = html.select(".infobox")[0]
        cover_img = detail_box_doms.select("a.cover")[0].get("href","").replace("//","")
        cover_img = "https://" + cover_img
        covers.append(cover_img)

        info_li_doms = detail_box_doms.select("#infobox > li")
        for li in info_li_doms:
            pre_fix = li.span.string
            if "中文名" in pre_fix:
                for string in li.strings:
                    if string == pre_fix: continue
                    title_chinese+=string
            if "作者" in pre_fix or "作画" in pre_fix or "原作" in pre_fix:
                for string in li.strings:
                    if string ==pre_fix: continue
                    author.append(string)
        desc_dom = html.select("#subject_summary")[0]
        for string in desc_dom.strings:
            desc += string

        for tag_dom in html.select(".subject_tag_section > .inner > a > span"):
            tags.append(tag_dom.string)
        book_info = {"title":title,"title_chinese":title_chinese,"author":author,"desc":desc,"tags":tags,"cover_img":cover_img}
        return book_info

    def get_book_info_from_mediaarts(self,book_id,type="manga"):
        if type=="manga":
            if isinstance(book_id,int):
                book_id = str(book_id)
            title = ""
            title_chinese = ""
            author = []
            desc = ""
            tags = []
            full_url = "https://%s/mg/comic_works/%s?display_view=pc&locale=ja" % (self.mediaarts_host,book_id)
            append_headers = {"Referer":"https://"+self.mediaarts_host,"Host":self.mediaarts_host}
            response = self.get(full_url,{**append_headers,**self.headers})
            response_text = response.content.decode("utf-8")

            html = BeautifulSoup(response_text,features="lxml")
            info_list_dom = html.select(".main tbody tr")
            for li in info_list_dom:
                pre_fix = li.th.string
                content = li.td.string
                if "マンガ作品名" == pre_fix: title = content
                #if '別題・副題・原題' == pre_fix and (content != "" or content != ""): title= " " + content + title
                if '著者（責任表示）' == pre_fix: author.append(content)

            book_info = {"title":title,"title_chinese":title_chinese,"author":author,"desc":desc,"tags":tags}
            return book_info

    def get_book_info_from_mangazenkan(self,book_id):
        title = ""
        title_chinese = ""
        author = []
        desc = ""
        tags = []
        end = False
        covers = []
        publisher = ''
        catalogs = []
        if 'http' in book_id:
            full_url = book_id
        else:
            full_url = "https://%s/item/%s.html" % (self.mangazenkan, book_id)

        append_headers = {"Referer":"https://"+self.mediaarts_host,"Host":self.mediaarts_host}
        response = self.get(full_url,{**append_headers,**self.headers})
        response_text = response.content.decode("utf-8")

        html = BeautifulSoup(response_text,features="lxml")
        title_li = html.select('ol.breadcrumb > li')[-1]
        title_a_url = title_li.a['href']
        query = urlsplit(title_a_url).query
        title = parse_qs(query).get('name')[0].replace("【入荷予約】","")
        print(title)

        title_h1 = html.select('div.product-detail h1')[0]
        if '全巻' in title_h1.string:
            end = True

        covers_li = html.select('ul.inline > li')
        for li in covers_li:
            img = li.select('img')[0]
            img_url = img['data-src'].replace("&quality=30",'')
            covers.append(img_url)
        if len(covers_li) == 0:
            cover_img = html.select('img.cover-image')
            if len(cover_img) > 0:
                covers.append(cover_img[0]['src'])
        if len( html.select('div[itemprop="description"]') )>0:
            desc_strings = html.select('div[itemprop="description"]')[0].stripped_strings
            for string in desc_strings:
                if string=='': continue
                desc += string +'\n'
            desc = desc[:-1]
        info_table_row = html.select('table.product-description')[0].select("tr")
        for row in info_table_row:
            head = row.th.string
            if '出版社' in head:
                publisher = row.td.a.string
            if 'カテゴリ' in head:
                a_s = row.select("a")
                for a in a_s:
                    catalogs.append(a.string.strip())
            if 'タグ' in head:
                a_s = row.select("a")
                for a in a_s:
                    tags.append(a.string.strip())
            if '作者' in head:
                a_s = row.select("a")
                for a in a_s:
                    author.append(a.string)


        book_info = {"title":title,"title_chinese":title_chinese,"author":author,"desc":desc,
                     "tags":tags,'end':end,'covers':covers,'publisher':publisher, 'catalogs':catalogs}
        return book_info


if __name__ == '__main__':
    rq = BookInfoSpider()
    res = rq.get_book_info_from_bangumi(135218)
    print(res)