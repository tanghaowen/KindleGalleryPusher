from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpRequest, HttpResponseRedirect
from account.models import User, MailVertifySendRecord, PasswordResetMailSendRecord
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from mainsite.models import ImageWithThumb
from django.core.files import File
from django.core.validators import validate_email, ValidationError
from pushmonitor.models import get_user_push_task_from_queue, get_global_push_tasks_from_queue, get_random_string


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

def account_activate(request):
    vid = request.GET.get("vid",None)
    token = request.GET.get("token",None)
    if vid is None or token is None or vid == '' or token == '': raise Http404
    mvr = get_object_or_404(MailVertifySendRecord,id=vid)
    if mvr.token == token:
        user_name = mvr.user_name
        email = mvr.email
        password = mvr.password
        if len(User.objects.filter(username=user_name)) > 0: return HttpResponse("您已激活账号")
        u = User(username=user_name,email=email)
        u.set_password(password)
        u.save()
        mvr.password=''
        mvr.save()
        login(request,u)

        return HttpResponseRedirect('/')

    else:
        raise Http404


def account_reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email',None)
        if email is None: raise Http404
        try:
            validate_email(email)
        except ValidationError:
            return HttpResponse("email can't use")

        user = User.objects.filter(email=email)
        if len(user)==0:
            return HttpResponse('email have no user')
        user = user[0]

        token =get_random_string(length=40)
        prmr = PasswordResetMailSendRecord(user=user,token=token)
        prmr.save()

        # 激活邮件
        reset_url = reverse('account:reset_password')
        host = request.get_host()
        reset_url ="http://"+ host + reset_url + '?prmr=%d&token=%s' % (prmr.id, token)
        html_body = """
        <h1>您好：</h1>
        <p>%s</p>
        <p>请点击下面的链接重置密码。</p>
        <a href='%s'>点击重置</a>
        <p>如果未显示按钮，请复制粘贴下面的地址到浏览器中激活账号：</p>
        <p>%s</p>
        """ % (user.username,reset_url,reset_url)
        plain_body = """您好：\n%s\n 请点击下面的链接重置密码。如果未显示超链接，请复制粘贴下面的地址到浏览器中激活账号: %s""" % (user.username,reset_url)
        print("重置密码token:",reset_url)
        print("开始发送激活邮件...")
        send_mail('漫推密码重置 - %s' % user.username,
                  plain_body,
                  'admin@asairo.net', [email], html_message=html_body,fail_silently=False)

        print("发送完毕")
        #login_res = login(request,new_user)
        #print("login res",login_res)
        return HttpResponse("ok")
    elif request.method == 'GET':
        return render(request,'accounts/forgot.html')
    raise Http404

def rest_password(request):
    if request.method == "GET":
        prmr_id = request.GET.get('prmr',None)
        token = request.GET.get('token',None)
        if prmr_id is None or token is None or prmr_id == '' or token == '':
            raise Http404
        prmr_id = int(prmr_id)
        prmr = get_object_or_404(PasswordResetMailSendRecord,id=prmr_id)
        if prmr.used : return HttpResponse("此链接已经使用过！")
        if prmr.token == token:
            password = get_random_string(length=12)
            prmr.user.set_password(password)
            prmr.user.save()
            prmr.used = True
            prmr.save()

            return HttpResponse("您的新密码为：%s。\n请尽快更改密码" % (password))
        else:
            return HttpResponse("此链接无效！")

    else:
        raise  Http404


def account_register(request : HttpRequest):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('main_site:home_page'))
        return render(request, 'accounts/register.html')
    elif request.method == 'POST':
        email = request.POST.get('email',"").strip()
        user_name = request.POST.get('username','').strip()
        password = request.POST.get('password',"")
        if user_name == "":
            return HttpResponse("username can't use!")
        if len(password)< 6:
            return HttpResponse("password too short!")
        if len(User.objects.filter(username=user_name)) > 0:
            return HttpResponse("same username already exits!")
        try:
            validate_email(email)
            if len(User.objects.filter(email=email)) > 0:
                return HttpResponse("email already used!")
        except ValidationError:
            return HttpResponse("email can't use")



        # new_user = User(username=user_name, password=password, email=email,is_active=False)
        # new_user.save()
        print("有新注册的账户: %s %s" % (user_name, email))
        token = get_random_string(length=40)
        mvr = MailVertifySendRecord(type='active',token=token, user_name=user_name, email=email,password=password)
        mvr.save()

        # 激活邮件
        active_url = reverse('account:active')
        host = request.get_host()
        active_url ="http://"+ host + active_url + '?vid=%d&token=%s' % (mvr.id, token)
        html_body = """
        <h1>您好：</h1>
        <p>%s</p>
        <p>感谢您注册漫推，请点击下面的链接激活账号。</p>
        <a href='%s'>点击激活</a>
        <p>如果未显示按钮，请复制粘贴下面的地址到浏览器中激活账号：</p>
        <p>%s</p>
        """ % (user_name,active_url,active_url)
        plain_body = """您好：\n%s\n感谢您注册漫推，请点击下面的链接激活账号。如果未显示超链接，请复制粘贴下面的地址到浏览器中激活账号: %s""" % (user_name,active_url)
        print("激活token:",active_url)
        print("开始发送激活邮件...")
        send_mail('漫推注册激活邮件 - %s' % user_name,
                  plain_body,
                  'admin@asairo.net', [email], html_message=html_body,fail_silently=False)

        print("发送完毕")
        #login_res = login(request,new_user)
        #print("login res",login_res)
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
        password = request.POST.get("password", None)
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
        if password is not None and len(password)>=6:
            user.set_password(password)

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






