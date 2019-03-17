import re
import time
from urllib.parse import quote, urlencode

from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.utils.timezone import now, timedelta

from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse, StreamingHttpResponse, FileResponse
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

DOWNLOAD_LINK_AVAILABLE_HOURS = 1

def home_page(request):
    homepage_book_groups = HomePageGroup.objects.all()
    side_special = HomePageSpecialSide.objects.all()
    recent_updated = Book.objects.filter(show=True).order_by('-update_time')[:18]

    context = { "homepage_book_groups":homepage_book_groups,
               "recent_updated":recent_updated,
                "side_special":side_special}
    return render(request,'mainsite/homepage.html', context=context)


def full_recently_updated_books(request):
    page_idx = request.GET.get("page",1)
    recent_updated = Book.objects.filter(show=True).order_by('-update_time')
    recent_updated_pages = Paginator(recent_updated,20)
    page = recent_updated_pages.get_page(page_idx)

    context = { "page":page,
                "title":'最近更新的漫画列表'}
    return render(request,'mainsite/book_list.html', context=context)



def search_page(request):
    if request.method != 'GET':
        raise Http404

    keyword = request.GET.get("keyword",None) # type:str
    author = request.GET.get("author",None) # type:str
    catalog = request.GET.get("catalog",None)
    tag = request.GET.get("tag",None)
    #keywords = keyword.split(' ')
    if keyword is None and author is None:
        books = []
        keyword = ""
    elif author is None and keyword is not None:
        books = Book.objects.filter(title__contains=keyword)
        keyword = keyword
    elif author is not None and keyword is None:
        books = Book.objects.filter(author__name__contains=author)
        keyword = "作者 %s" % ( author)
    elif author is not None and keyword is not None:
        books = Book.objects.filter(author__name__contains=author, title__contains=keyword)
        keyword = "%s %s" % (keyword, author)

    if catalog is not None:
        books = Book.objects.filter(tags__name__contains=catalog,tags__group = 'catalog')
        keyword =  "分类 %s" % ( catalog)
    if tag is not None:
        books = Book.objects.filter(tags__name__contains=tag, tags__group__isnull=True)
        keyword = "标签 %s" % (tag)
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
    elif site == 'mangazenkan':
        book_info = rq.get_book_info_from_mangazenkan(site_id)
        book.mangazenkan_site_path = site_id
    else:
        raise Http404("指定的网站不存在")

    print(book_info)
    if "covers" in book_info:
        total_covers_num = len(book_info['covers'])
        print("有封面，共%d张" % total_covers_num)
        for idx,cover_url in enumerate(book_info['covers']):
            print("%d/%d 开始下载封面" % (idx+1, total_covers_num))
            print(cover_url)
            p, ext = os.path.splitext( os.path.basename(cover_url) )
            try:
                cover_response = rq.get(cover_url,headers={},stream=True)
                if cover_response.status_code == 200:
                    print("下载成功")
                    f_memo = BytesIO(cover_response.content)
                    f_memo.seek(0)
                    image_already_in_database = ImageWithThumb.image_already_in_database(f_memo)
                    if image_already_in_database:
                        print("此图片已经存在于图库中！开始检测是否存在于这本书中！")
                        res = book.covers.filter(id=image_already_in_database.id)
                        if len(res)>0:
                            print('此图片已和这本书关联，跳过！')
                        else:
                            print("此图片未和这本书关联，将此图片关联到书本")
                            book.covers.add(image_already_in_database)
                            book.setCover(image_already_in_database.id)
                            book.save()
                    else:
                        image = ImageWithThumb(image=File(f_memo, "tmp" + ext), thumb_image=File(None, None),normal_image=File(None,None))
                        image.save()
                        book.covers.add(image)
                        book.setCover(image.id)
                else:
                    print("下载失败")
            except Exception as e:
                print(e)
                print("下载失败")




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
    if request.method == "POST":
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


@login_required()
def volume_download(request):
    if request.method == 'GET':
        user = request.user
        volume_id = int(request.GET.get('volume_id',''))
        type = request.GET.get('type','')
        volume = get_object_or_404(Volume,id=volume_id)
        # 虽然名叫add，但实际上如果指定时间之内已经下载过的话的，并不会消费流量，True为可以提供下载
        # False为不能下载，得POST后再下
        res = user.have_cost_bandwidth_recently(volume)
        if res:
            file = None
            if type == 'zip':
                file = volume.zip_file
            elif type == 'mobi':
                file = volume.mobi_file
            elif type == 'mobi_push':
                file = volume.mobi_push_file
            elif type == 'epub':
                file = volume.epub_file
            else:
                raise Http404
            file_body, file_ext = os.path.splitext(file.name)
            attachment_filename = "[%s] %s %s%s" % (volume.book.get_authors_string(),
                                                    volume.book.title,
                                                    volume.name,
                                                    file_ext)
            print("附件名称:",attachment_filename)

            response = HttpResponse()
            try:
                attachment_filename.encode('ascii')
                file_expr = 'filename="{}"'.format(attachment_filename)
            except UnicodeEncodeError:
                file_expr = "filename*=utf-8''{}".format(quote(attachment_filename))
            response['Content-Disposition'] = 'attachment; {}'.format(file_expr)
            #response['Content-Type'] = 'application/octet-stream'
            #response['Content-Length'] = file.size
            file_path_url = quote(file.name)
            print(file_path_url)
            response['X-Accel-Redirect'] = '/donwloadbook/%s' % file_path_url
            print("X-ACCEL:",response['X-Accel-Redirect'])
            #response['Content-Type'] = 'application/octet-stream'
            #response['Content-Disposition'] = 'attachment;filename="%s"' %  attachment_filename

            return response
        else:
            raise Http404
    if request.method == 'POST':
        user = request.user
        volume_id = int(request.POST.get('volume_id',''))
        volume_type = request.POST.get('type','')
        if volume_type not in [VOLUME_TYPE_MOBI,VOLUME_TYPE_ZIP, VOLUME_TYPE_EPUB]: raise Http404
        volume = get_object_or_404(Volume,id=volume_id)

        #res = user.add_bandwidth_cost(volume)
        cost_res = user.bandwidth_cost(volume,'download',volume_type)
        status = cost_res['status']
        # BANDWIDTH_COST为流量消耗成功了  BANDWIDTH_NO_COST为最近已经消费过不必消费流量
        if status == BANDWIDTH_COST or status == BANDWIDTH_NO_COST :
            return HttpResponse("ok")
        elif status == BANDWIDTH_NOT_ENOUGH:
            return HttpResponse("bandwidth not enough")
        elif status == ONLY_VIP:
            return HttpResponse("only vip")
        elif status == ERROR:
            raise Http404
        else:
            raise Http404
    raise Http404


# TODO: 因为只有我一个人上传，所以这里直接判断用户admin就行
# 如果今后要增加协助者，得做好完整的权限判断
@login_required
def upload_file_old(request,book_id):
    if request.user.username != 'admin': raise Http404

    if request.method == "GET":
        book = get_object_or_404(Book,id=book_id)
        context = {"book":book}
        return render(request,'mainsite/upload_page.html',context=context)
    elif request.method == 'POST':
        volume_type = request.POST.get("volume_type",None)
        zip_FILE = request.FILES.get("zip_file",None)
        if book_id is None or volume_type is None or zip_FILE is None: raise Http404
        book = get_object_or_404(Book, id = book_id)
        volume_type_obj = get_object_or_404(VolumeType, name=volume_type)
        volume = Volume( book=book,type=volume_type_obj,zip_file=zip_FILE )
        volume.save()
        return HttpResponse("OK")

@login_required
def upload_file(request,book_id):
    if request.method == 'GET':
        if request.user.username != "admin": raise Http404
        book = get_object_or_404(Book,id=book_id)
        context = {"book":book}
        return render(request,'mainsite/upload_by_localfile.html',context=context)
    elif request.method == 'POST':
        if request.user.username != "admin": raise Http404
        book = get_object_or_404(Book, id=book_id)
        local_path = request.POST.get("path",None)
        action = request.POST.get("action",None)
        if action == 'show':
            files = []
            pattern = re.compile(r'\d+')
            for f in os.listdir(local_path):
                full_path = os.path.join(local_path,f)
                if not os.path.isfile(full_path): continue
                fl = []
                fl.append(f)
                res = pattern.findall(f)
                if len(res)>0: volume_number = int(res[0])
                else: volume_number=-1
                fl.append(volume_number)
                files.append(fl)

            return render(request,'mainsite/upload_by_localfile_show_list.html',context={"book":book,"files":files, "path":local_path})
        elif action == 'set':
            v = Volume()
            files = []
            pattern = re.compile(r'\d+')
            for f in os.listdir(local_path):
                full_path = os.path.join(local_path,f)
                if not os.path.isfile(full_path): continue
                fl = []
                fl.append(f)
                res = pattern.findall(f)
                if len(res)>0: volume_number = int(res[0])
                else: volume_number=-1
                fl.append(volume_number)
                files.append(fl)
            volume_type = VolumeType.objects.get(name='单行本')
            for f in files:
                file, volume_number = f
                full_path = os.path.join(local_path, file)
                fh = open(full_path,'rb')
                zip_file = File(fh,name=file)
                v = Volume(book=book,name="",volume_number=str(volume_number), type=volume_type,
                           zip_file=zip_file)
                v.save()
            return HttpResponse("成功")
    raise Http404

@login_required
def upload_file_set(request,book_id):
    pass

@csrf_exempt
def show_bandwidth_rule(request):
    return render(request,'mainsite/bandwidth_rule.html')

@csrf_exempt
def feedback(request):
    if request.method == "GET":
        return render(request,'mainsite/feedback.html')
    elif request.method == "POST":
        email = request.POST.get("email",'无邮箱')
        message = request.POST.get("message","无内容")
        user = request.user
        id = -1 if user.id is None else user.id
        username = '游客用户' if user.id is None else user.username
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            ip = request.META['REMOTE_ADDR']
        send_mail('漫推 - 有用户反馈问题了:%s' % username,
                  "用户ID:%d 用户名%s \n 对方联系方式: %s  IP:%s\n反馈问题:\n%s" % (id,username,email,ip,message),
                  'admin@asairo.net', ['tanghaowen100@gmail.com'],fail_silently=True)
        if user.id is not None:
            ufeed = UserFeedback(email=email,ip=ip,message=message,user=user)
        else:
            ufeed = UserFeedback(email=email, ip=ip, message=message, user=None)
        ufeed.save()
        return render(request,'mainsite/feedback_ok.html')