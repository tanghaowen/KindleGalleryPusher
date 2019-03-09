from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse
# Create your views here.
from . import tools
from django.views.decorators.csrf import csrf_exempt
import json
from .models import *
from django.shortcuts import get_object_or_404, render
from .tools import get_hash_filename
import itertools
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from account.models import *
from pushmonitor.models import put_task_to_push_queue

def home_page(request):
    homepage_book_groups = HomePageGroup.objects.all()
    recent_updated = Book.objects.filter(show=True).order_by('-update_time')
    book = Book.objects.get(id=1)
    books = [book for i in range(0,10)]
    headers = [book for i in range(0,3)]

    print(headers)
    context = {"banner":books,
               "homepage_book_groups":homepage_book_groups,
               "recent_updated":recent_updated}
    return render(request,'mainsite/homepage.html', context=context)


def search_page(request):
    if request.method != 'GET':
        raise Http404

    keyword = request.GET.get("keyword",None) # type:str
    author = request.GET.get("author",None) # type:str
    #keywords = keyword.split(' ')
    if keyword is None and author is None:
        books = []
        keyword = ""
    if author is None and keyword is not None:
        books = Book.objects.filter(title__contains=keyword)
        keyword = keyword
    if author is not None and keyword is None:
        books = Book.objects.filter(author__name__contains=author)
        keyword = author
    if author is not None and keyword is not None:
        books = Book.objects.filter(author__name__contains=author, title__contains=keyword)
        keyword = "%s %s" % (keyword, author)
    context = {"books":books,
               "keyword":keyword}
    return render(request, 'mainsite/search_res.html',context=context)


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



def book_info(request,book_id):
    book = get_object_or_404( Book, id=book_id) # type:Book

    user = request.user


    cover_id = book.cover_id
    try:
        cover_image = ImageWithThumb.objects.get(id=cover_id)
    except ImageWithThumb.DoesNotExist:
        # TODO: 没有图片的时候，显示默认的封面
        cover_image = False

    volumes_dict = {}
    volumes = Volume.objects.filter(book=book_id,show=True)
    type_list = itertools.groupby(volumes.values_list('type__name',flat=True))

    # values_list
    for type_string, iter in type_list:
        v = Volume.objects.filter(book=book_id,show=True,type__name=type_string)
        volumes_dict[type_string] = v
    context = {"book":book,
               "cover_image":cover_image,
               "volumes_dict":volumes_dict,
               "user":user}
    print(volumes_dict)

    return render(request,'mainsite/book_info.html',context)

@login_required()
def book_subscribe(request, book_id):
    if request.method == "GET":
        # TODO: 如果今后有时间的话，可以搞个获取订阅者列表的接口
        raise Http404
    elif request.method == "POST":
        user = request.user # type:User
        if len(user.subscriptes.filter(id=book_id)) == 0:
            book = get_object_or_404(Book, id=book_id)
            user.subscriptes.add(book)
            user.save()
            return HttpResponse("ok")
    elif request.method == "DELETE":
        user = request.user  # type:User
        if len(user.subscriptes.filter(id=book_id)) > 0:
            book = get_object_or_404(Book, id=book_id)
            user.subscriptes.remove(book)
            user.save()
            return HttpResponse("ok")
    raise Http404


@login_required()
def book_collect(request, book_id):
    if request.method == "GET":
        # TODO: 如果今后有时间的话，可以搞个获取收藏者列表的接口
        raise Http404
    elif request.method == "POST":
        user = request.user # type:User
        if len(user.collections.filter(id=book_id)) == 0:
            book = get_object_or_404(Book, id=book_id)
            user.collections.add(book)
            user.save()
            return HttpResponse("ok")
    elif request.method == "DELETE":
        user = request.user  # type:User
        if len(user.collections.filter(id=book_id)) > 0:
            book = get_object_or_404(Book, id=book_id)
            user.collections.remove(book)
            user.save()
            return HttpResponse("ok")
    raise Http404


@login_required()
def book_comment(request, book_id):
    if request.method == "GET":
        # TODO: 如果今后有时间的话，可以搞个获取书籍评论列表的功能
        raise Http404
    elif request.method == "POST":
        user = request.user # type:User
        message = request.POST.get("message",None)# type:str
        if message is not None and (message.replace(" ","").replace("　","") != ""):
            book = get_object_or_404(Book, id=book_id)
            comment = Comment(book=book, user=user, message=message)
            comment.save()
            return HttpResponse("ok")
    raise Http404


@login_required()
def book_score(request, book_id):
    if request.method == "GET":
        # TODO: 如果今后有时间的话，可以搞个获取书籍评论列表的功能
        raise Http404
    elif request.method == "POST":
        book = get_object_or_404(Book, id=book_id)
        user = request.user # type:User
        score = request.POST.get("score","")
        try:
            score = int(score)
        except ValueError:
            raise Http404
        if score<1: score = 1
        if score>5: score = 5

        query = Score.objects.filter(user=user,book=book)
        if len(query) >0 :
            score_obj = query[0]
            score_obj.score = score
        else:
            score_obj = Score(score=score,book=book,user=user)
        score_obj.save()
        return HttpResponse("ok")
    raise Http404


@login_required()
def book_push(request, book_id):
    if request.method == "GET":
        raise Http404
    elif request.method == "POST":
        volume_id = request.POST.get("volume_id",None)
        force_push = request.POST.get("fore_push",False)
        if force_push == 'true': force_push = True
        else: force_push = False
        if volume_id is None: raise Http404
        book = get_object_or_404(Book, id=book_id)
        volume = get_object_or_404(Volume, id=volume_id)
        user = request.user
        push_res = put_task_to_push_queue(user, volume,force_push)
        if push_res == 'pending':
            return HttpResponse("Already in queue!")
        if push_res =='doing':
            return HttpResponse("Now in pushing!")
        if push_res == 'done':
            return HttpResponse("Have pushed before!")
        if push_res == 'bandwidth less':
            return HttpResponse("bandwidth less!")
        if push_res == 'no kindle email':
            return HttpResponse("No kindle email!")
        if push_res == 'ok':
            return HttpResponse("ok")
    raise Http404

