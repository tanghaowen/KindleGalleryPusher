from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpRequest, HttpResponseRedirect
from account.models import User
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from mainsite.models import ImageWithThumb
from django.core.files import File
from django.core.validators import validate_email, ValidationError
from pushmonitor.models import get_user_push_task_from_queue, get_global_push_tasks_from_queue


def account_login(request : HttpRequest):
    if request.method == 'GET':
        redirect_path = request.GET.get("next")
        if redirect_path == "": redirect_path = None
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('main_site:home_page'))
        return render(request,'accounts/login.html',context={"redirect_path":redirect_path})
    elif request.method == 'POST':
        user_name = request.POST['username']
        password = request.POST['password']
        user = authenticate(request,username = user_name, password=password)
        if user is not None:
            login_res = login(request,user)
            print("login res",login_res)
            return HttpResponse("login success")
        else:
            return HttpResponse("Login Failed. Error username or password!",status=401)
    else:
        raise Http404


def account_register(request : HttpRequest):
    if request.method == 'GET':
        return render(request, 'accounts/register.html')
    elif request.method == 'POST':
        user_name = request.POST.get('username',"")
        password = request.POST.get('password',"")
        user_name = user_name.replace(" ","").replace("　","")
        if user_name == "":
            return HttpResponse("username can't use!")
        if len(password)< 6:
            return HttpResponse("password too short!")
        if len(User.objects.filter(username=user_name)) > 0:
            return HttpResponse("same username already exits!")

        new_user = User(username=user_name, password=password)
        new_user.save()
        login_res = login(request,new_user)
        print("login res",login_res)
        return HttpResponse("ok")
    else:
        raise Http404


@login_required
def set_self_account(request):
    user =  request.user # type: User

    context = {'user':user,
               'edit':True}
    return render(request,'accounts/profile.html',context=context)


def account_profile(request,uid):
    user = get_object_or_404(User, id=uid)

    context = {'user':user,
               'edit':False}
    return render(request,'accounts/profile.html',context=context)

@login_required
def account_logout(request):
    user = request.user
    res = logout(request)
    return HttpResponseRedirect('/')



@login_required
def set_profile(request):
    if request.method == "GET":
        return HttpResponseRedirect(reverse('account:self_profile'))
    if request.method == "POST":
        # 只能改变自己这个账号的信息，不同改变其他别人账号的信息
        user = request.user
        nick_name = request.POST.get("nick_name",None)# type: str
        signature = request.POST.get("signature",None)
        avatar = request.FILES.get("avata",None)
        kindle_email = request.POST.get("kindle_email",None)
        has_same_name_user = False

        if nick_name is not None and nick_name.replace(" ","").replace("　","") !="":
            nick_name = nick_name.replace(" ","").replace("　","")
            # 检测是否有同名的用户名
            other_users = User.objects.filter(nick_name=nick_name)
            if len(other_users)>0:
                has_same_name_user = True
            else:
                user.nick_name = nick_name

        if signature is not None:
            user.signature = signature

        if avatar is not None:
            avatatr_image = ImageWithThumb(image=avatar,thumb_image=File(None,None),normal_image=File(None,None),type='avatar')
            avatatr_image.save()
            user.avatar = avatatr_image

        if kindle_email is not None:
            if kindle_email == '': user.kindle_email = None
            else:
                try:
                    validate_email(kindle_email)
                    if '@kindle.' in kindle_email:
                        user.kindle_email = kindle_email
                except ValidationError:
                    print("用户输入的邮箱地址不合规范")
        user.save()
        return HttpResponseRedirect(reverse('account:self_profile'))
    else:
        raise Http404


@login_required
def push_queue(request):
    user = request.user
    page_idx = request.GET.get('page',1)
    is_global = request.GET.get('global',0)
    import time
    start_time = time.time()

    if is_global == '1' and user.username == 'admin':
        user_tasks = get_global_push_tasks_from_queue()
        is_global = True
    else:
        user_tasks = get_user_push_task_from_queue(user)
        is_global = False

    print("数据检索耗时",time.time()-start_time)
    start_time = time.time()
    pages = Paginator(user_tasks,20)
    page = pages.get_page(page_idx)
    context = {"tasks":user_tasks,
               "user":user,
               'page':page,
               'is_global':is_global}
    c = render(request, 'accounts/push_queue.html',context=context)
    print("生成模板耗时",time.time()-start_time)
    return c

