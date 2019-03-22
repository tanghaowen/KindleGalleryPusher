from django.core.mail import send_mail
from django.core.paginator import Paginator

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpRequest, HttpResponseRedirect
from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt

from account.models import User, MailVertifySendRecord, PasswordResetMailSendRecord, ChargeRecord, CHARGE_MODE_VIP, \
    AccountRegisterIpRecord, get_unique_invite_code, USER_BASE_BANDWIDTH, INVITED_USER_BASE_BANDWIDTH
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from mainsite.models import ImageWithThumb
from django.core.files import File
from django.core.validators import validate_email, ValidationError
from pushmonitor.models import get_user_push_task_from_queue, get_global_push_tasks_from_queue, get_random_string


def account_login(request: HttpRequest):
    if request.method == 'GET':
        redirect_path = request.GET.get("next")
        if redirect_path == "": redirect_path = None
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('main_site:home_page'))
        return render(request, 'accounts/login.html', context={"redirect_path": redirect_path})
    elif request.method == 'POST':
        user_name = request.POST['username']
        password = request.POST['password']
        try:
            validate_email(user_name)
            users = User.objects.filter(email=user_name)
            if len(users) == 0:
                return HttpResponse("Login Failed. Error username or password!", status=401)
            else:
                user = authenticate(request, username=users[0].username, password=password)
        except ValidationError:
            user = authenticate(request, username=user_name, password=password)
        if user is not None:
            login_res = login(request, user)
            print("login res", login_res)
            return HttpResponse("login success")
        else:
            return HttpResponse("Login Failed. Error username or password!", status=401)
    else:
        raise Http404


def account_activate(request):
    vid = request.GET.get("vid", None)
    token = request.GET.get("token", None)
    if vid is None or token is None or vid == '' or token == '': raise Http404
    mvr = get_object_or_404(MailVertifySendRecord, id=vid)
    if mvr.token == token:
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            ip = request.META['REMOTE_ADDR']
        print('有用户点击了激活链接，ip:')
        print(ip)
        print("token", token)

        user_name = mvr.user_name
        email = mvr.email
        password = mvr.password
        inviter = mvr.who_inviter
        print(user_name, email)
        print("邀请者", inviter)
        # if len(User.objects.filter(username=user_name)) > 0: return HttpResponse("您已激活过账号")

        ips = AccountRegisterIpRecord.objects.filter(reg_date__date=timezone.datetime.today(),
                                                     ip=ip, action='active')
        print('此ip今日激活账号数量:%s' % len(ips))
        if len(ips) >= 1:
            return HttpResponse("何回もアカウントを作らないでください！")
        new_user_invite_code = get_unique_invite_code()

        u = User(username=user_name, email=email, invite_code=new_user_invite_code, inviter=inviter)
        u.set_password(password)
        if inviter is None:
            u.bandwidth_tmp = USER_BASE_BANDWIDTH
        else:
            u.bandwidth_tmp = INVITED_USER_BASE_BANDWIDTH
        u.save()
        mvr.password = ''
        mvr.save()
        login(request, u)
        r = AccountRegisterIpRecord(ip=ip, action='active')
        r.save()
        send_mail('KindleGalleryPusher - 新用户注册：%s' % user_name,
                  "新用户注册:%s" % user_name,
                  'admin@lpanda.net', ['tanghaowen100@gmail.com'], fail_silently=True)

        return HttpResponseRedirect('/')

    else:
        raise Http404


def account_reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', None)
        if email is None: raise Http404
        try:
            validate_email(email)
        except ValidationError:
            return HttpResponse("email can't use")

        user = User.objects.filter(email=email)
        if len(user) == 0:
            return HttpResponse('email have no user')
        user = user[0]

        token = get_random_string(length=40)
        prmr = PasswordResetMailSendRecord(user=user, token=token)
        prmr.save()

        # 激活邮件
        reset_url = reverse('account:reset_password')
        host = request.get_host()
        reset_url = "http://" + host + reset_url + '?prmr=%d&token=%s' % (prmr.id, token)
        html_body = """
        <h1>KindleGalleryPusher：</h1>
        <p>%s</p>
        <p>下のリンクをクリックして、パスワードをリセットしてください。</p>
        <a href='%s'>リセット</a>
        <p></p>
        <p>%s</p>
        """ % (user.username, reset_url, reset_url)
        plain_body = """KindleGalleryPusherへ\n%s\n 下のリンクをクリックして、パスワードをリセットしてください。 %s""" % (user.username, reset_url)
        print("重置密码token:", reset_url)
        print("开始发送激活邮件...")
        send_mail('KindleGalleryPusherパスワードリセット - %s' % user.username,
                  plain_body,
                  'admin@lpanda.net', [email], html_message=html_body, fail_silently=False)

        print("发送完毕")
        # login_res = login(request,new_user)
        # print("login res",login_res)
        return HttpResponse("ok")
    elif request.method == 'GET':
        return render(request, 'accounts/forgot.html')
    raise Http404


def rest_password(request):
    if request.method == "GET":
        prmr_id = request.GET.get('prmr', None)
        token = request.GET.get('token', None)
        if prmr_id is None or token is None or prmr_id == '' or token == '':
            raise Http404
        prmr_id = int(prmr_id)
        prmr = get_object_or_404(PasswordResetMailSendRecord, id=prmr_id)
        if prmr.used: return HttpResponse("此链接已经使用过！")
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
        raise Http404


def account_register(request: HttpRequest):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('main_site:home_page'))
        invite_code = request.GET.get('code', None)
        context = {"invite_code": invite_code}

        return render(request, 'accounts/register.html', context=context)
    elif request.method == 'POST':
        email = request.POST.get('email', "").strip()
        user_name = request.POST.get('username', '').strip()
        password = request.POST.get('password', "")
        invite_code = request.POST.get('invite_code', None)
        inviter = None
        if invite_code is not None:
            inviters = User.objects.filter(invite_code=invite_code)
            if len(inviters) > 0:
                inviter = inviters[0]

        # 获取用户的ip
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            ip = request.META['REMOTE_ADDR']
        print('有新用户发送注册邮件，ip:')
        print(ip)
        ips = AccountRegisterIpRecord.objects.filter(reg_date__date=timezone.datetime.today(),
                                                     ip=ip, action='mail')
        # ips = AccountRegisterIpRecord.objects.filter(ip=ip,date__date=timezone.datetime.date.today(),action='mail')

        print('此ip今日发送邮件数量%d' % len(ips))
        if len(ips) > 10:
            print('此地址今天请求发送邮件数量超过10封')
            return HttpResponse("mail over limit")

        if user_name == "":
            return HttpResponse("username can't use!")
        try:
            validate_email(user_name)
            return HttpResponse("don't use email as username")
        except ValidationError:
            pass
        if len(password) < 6:
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
        mvr = MailVertifySendRecord(type='active', token=token, user_name=user_name, email=email, password=password,
                                    who_inviter=inviter)
        mvr.save()

        # 激活邮件
        active_url = reverse('account:active')
        host = request.get_host()
        active_url = "http://" + host + active_url + '?vid=%d&token=%s' % (mvr.id, token)
        html_body = """
        <p>KindleGalleryPusher</p>
        <p>%s</p>
        <p>KindleGalleryPusherへようこそ，下のリンクをクリックして、アカウントを有効にしてください。</p>
        <a href='%s'>アカウントを有効にする</a>
        <p></p>
        <p>%s</p>
        """ % (user_name, active_url, active_url)
        plain_body = """KindleGalleryPusher　\n%s\nKindleGalleryPusherへようこそ，下のリンクをクリックして、アカウントを有効にしてください: %s""" % (
        user_name, active_url)
        print("激活token:", active_url)
        print("开始发送激活邮件...")
        send_mail('KindleGalleryPusherへようこそ - %s' % user_name,
                  plain_body,
                  'admin@lpanda.net', [email], html_message=html_body, fail_silently=False)

        print("发送完毕")
        ip_record = AccountRegisterIpRecord(action='mail', ip=ip)
        ip_record.save()
        # login_res = login(request,new_user)
        # print("login res",login_res)
        return HttpResponse("ok")
    else:
        raise Http404


@login_required
def set_self_account(request):
    user = request.user  # type: User
    collections = user.collections.all()[:12]
    subscs = user.subscriptes.all()[:12]
    context = {'user': user,
               'edit': True,
               'collections': collections,
               'subscs': subscs}
    return render(request, 'accounts/profile.html', context=context)


def account_profile(request, uid):
    user = get_object_or_404(User, id=uid)
    collections = user.collections.all()[:12]
    subscs = user.subscriptes.all()[:12]
    context = {'user': user,
               'edit': False,
               'collections': collections,
               'subscs': subscs}

    return render(request, 'accounts/profile.html', context=context)


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
        nick_name = request.POST.get("nick_name", None)  # type: str
        signature = request.POST.get("signature", None)
        avatar = request.FILES.get("avata", None)
        kindle_email = request.POST.get("kindle_email", None)
        password = request.POST.get("password", None)
        has_same_name_user = False

        if nick_name is not None and nick_name.replace(" ", "").replace("　", "") != "":
            nick_name = nick_name.replace(" ", "").replace("　", "")
            # 检测是否有同名的用户名
            other_users = User.objects.filter(nick_name=nick_name)
            if len(other_users) > 0:
                has_same_name_user = True
            else:
                user.nick_name = nick_name

        if signature is not None:
            user.signature = signature

        if avatar is not None:
            avatatr_image = ImageWithThumb(image=avatar, thumb_image=File(None, None), normal_image=File(None, None),
                                           type='avatar')
            avatatr_image.save()
            user.avatar = avatatr_image

        if kindle_email is not None:
            if kindle_email == '':
                user.kindle_email = None
            else:
                try:
                    validate_email(kindle_email)
                    if '@kindle.' in kindle_email:
                        user.kindle_email = kindle_email
                except ValidationError:
                    print("用户输入的邮箱地址不合规范")
        if password is not None and len(password) >= 6:
            user.set_password(password)

        user.save()
        return HttpResponseRedirect(reverse('account:self_profile'))
    else:
        raise Http404


@login_required
def push_queue(request):
    user = request.user
    page_idx = request.GET.get('page', 1)
    is_global = request.GET.get('global', 0)
    import time
    start_time = time.time()

    if is_global == '1' and user.username == 'admin':
        user_tasks = get_global_push_tasks_from_queue()
        is_global = True
    else:
        user_tasks = get_user_push_task_from_queue(user)
        is_global = False

    print("数据检索耗时", time.time() - start_time)
    start_time = time.time()
    pages = Paginator(user_tasks, 20)
    page = pages.get_page(page_idx)
    context = {"tasks": user_tasks,
               "user": user,
               'page': page,
               'is_global': is_global}
    c = render(request, 'accounts/push_queue.html', context=context)
    print("生成模板耗时", time.time() - start_time)
    return c


@login_required
def bandwidth_cost_records(request):
    user = request.user
    page_idx = request.GET.get('page', 1)
    is_global = request.GET.get('global', 0)

    records = user.get_uer_bandwidth_records()

    pages = Paginator(records, 20)
    page = pages.get_page(page_idx)
    context = {"records": records,
               "user": user,
               'page': page, }
    c = render(request, 'accounts/bandwidth_records.html', context=context)

    return c


@login_required
def kakin(request):
    if request.method == 'GET':
        mode = request.GET.get("mode", None)
        if mode is None: raise Http404
        if mode == 'vip':
            user = request.user
            price = 0.1
            price_string = str(price)

            order_id = user.username + "-" + get_random_string(length=10)
            order_url = 'https://codepay.fateqq.com/creat_order/creat_order/?id=194647&type=1&price=%s&pay_id=%s&token=IyncS6FVdsVrz6wGOLZLx6Km9M1j1O3f' % (
            price_string, order_id)
            print("订单URL")
            print(order_url)
            context = {'user': user,
                       'order_url': order_url,
                       'order_id': order_id}
            crd = ChargeRecord(user=user, price=price, content='测试订单', order_id=order_id)
            crd.save()
            return render(request, 'accounts/kakin_page.html', context=context)
        else:
            raise Http404
    raise Http404


@csrf_exempt
def payok(request):
    """
    <QueryDict: {'app_time': ['1552472848'], 'chart': ['utf-8'], 'id': ['194647'], 'money': ['0.11'], 'pay_id': ['admin-2ep7tkLPIR'], 'pay_no': ['2019031322001458761021330417'], 'pay_time': ['1552469228'], 'price': ['0.1'], 'status': ['1'], 'tag': ['0'], 'trade_no': ['1155246920711946475526273402'], 'trueID': ['194647'], 'type': ['1'], 'version': ['6.400'], 'sign': ['86fc9304b1f129f8c22368ec6c61726e']}>
    :param request:
    :return:
    """
    print(request.POST)
    print("有新的付款成功订单！")
    order_id = request.GET.get('pay_id')
    print("order id", order_id)
    charge_record = get_object_or_404(ChargeRecord, order_id=order_id)
    status = request.GET.get('status', '0')
    if status is not None and status == '1':
        print("订单状态为1，成功")
        price = request.GET.get('price')
        charge_record.status = 'ok'
        charge_record.payed = True
        charge_record.save()
        charge_record.user.charge_bandwidth(CHARGE_MODE_VIP)
        send_mail('KindleGalleryPusher - 有用户氪金拉！ %s' % order_id,
                  "KindleGalleryPusher - 有用户氪金拉！",
                  'admin@lpanda.net', ['tanghaowen100@gmail.com'], fail_silently=True)


    else:
        print('订单状态为0，失败')
        charge_record.payed = False
        charge_record.status = 'error'
        return HttpResponse("ok")
    return HttpResponse('ok')


@login_required
def precharge(request):
    if request.method == 'GET':
        user = request.user
        context = {'user': user}
        return render(request, 'accounts/precharge.html', context)
    raise Http404


@login_required
def full_collection(request):
    page_idx = request.GET.get("page", 1)
    uid = request.GET.get('uid', None)
    try:
        uid = int(uid)
    except (ValueError, TypeError):
        user = request.user
        collections = user.collections.all()
    else:
        user = get_object_or_404(User, id=uid)
        collections = user.collections.all()

    collections_pages = Paginator(collections, 20)
    page = collections_pages.get_page(page_idx)

    context = {"page": page,
               "title": '%s 的收藏列表' % user.username}
    return render(request, 'mainsite/book_list.html', context=context)


@login_required
def full_subscs(request):
    page_idx = request.GET.get("page", 1)
    uid = request.GET.get('uid', None)
    try:
        uid = int(uid)
    except  (ValueError, TypeError):
        user = request.user
        subscriptes = user.subscriptes.all()
    else:
        user = get_object_or_404(User, id=uid)
        subscriptes = user.subscriptes.all()

    subscriptes_pages = Paginator(subscriptes, 20)
    page = subscriptes_pages.get_page(page_idx)

    context = {"page": page,
               "title": '%s 的订阅列表' % user.username}
    return render(request, 'mainsite/book_list.html', context=context)
