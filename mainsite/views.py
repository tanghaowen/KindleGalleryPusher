from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse
# Create your views here.
from . import tools
from django.views.decorators.csrf import csrf_exempt
import json
from .models import *
from django.shortcuts import get_object_or_404, render
from .tools import get_hash_filename

def home_page(request):
    return HttpResponse("Hello Home Page")

@csrf_exempt
def get_info_from_online(request,book_id):
    if request.method != "POST":
        raise Http404("Error!")
    site = request.POST.get("site",None)
    site_id = request.POST.get("book_id",None)
    if site is None or site_id is None: raise Http404("缺少网站书籍id或者网站信息！")

    book = get_object_or_404(Book, id=book_id)
    rq = tools.BookInfoSpider()
    if site == "bangumi":
        book_info = rq.get_book_info_from_bangumi(site_id)
        book.bangumi_site_path = int(site_id)
    elif site == "mediaarts":
        book_info = rq.get_book_info_from_mediaarts(site_id)
        book.mediaarts_site_path = int(site_id)
    else:
        raise Http404("指定的网站不存在")

    if "cover_img" in book_info:
        print("开始下载封面")
        cover_url = book_info.get("cover_img")
        p, ext = os.path.splitext( os.path.basename(cover_url) )
        cover_response = rq.get(cover_url,headers={},stream=True)
        if cover_response.status_code == 200 :
            print("下载成功")
            f_memo = BytesIO(cover_response.content)
            image = ImageWithThumb(image=File(f_memo,"tmp"+ext),thumb_image=File(None,None))
            image.save()
            book.covers.add( image )
            book.setCover(image.id)

    book.set_book_info(book_info)
    return HttpResponse("OK")

@csrf_exempt
def book_info(request,book_id):
    book = get_object_or_404( Book, id=book_id)
    cover_id = book.cover_id
    try:
        cover_image = ImageWithThumb.objects.get(id=cover_id)
    except ImageWithThumb.DoesNotExist:
        cover_image = False


    volumes = Volume.objects.filter(book=book_id)
    context = {"book":book,
               "cover_image":cover_image,
               "volumes":volumes}


    return render(request,'mainsite/book_info.html',context)


