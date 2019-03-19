from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
from django.utils.crypto import get_random_string

from mainsite.models import *
from django.utils.timezone import now, timedelta
from django.core.validators import validate_email


DOWNLOAD_LINK_AVAILABLE_HOURS = 1
ACCOUNT_ACTIVATE_TOKEN_AVAILABLE_HOURS = 1
USER_BASE_BANDWIDTH = 200
INVITED_USER_BASE_BANDWIDTH = 500
VIP_PLUS_BANDWIDTH = 20 * 1024
CHARGE_MODE_VIP = 1

BANDWIDTH_NO_COST = 0
BANDWIDTH_COST = 1
BANDWIDTH_NOT_ENOUGH = 2
ONLY_VIP =4
ERROR = 3

VOLUME_TYPE_ZIP = 'zip'
VOLUME_TYPE_MOBI = 'mobi'
VOLUME_TYPE_EPUB = 'epub'

def get_unique_invite_code():
    """
    获取随机的邀请码，如果数据库里已经存在了则循环获取
    :return:
    """
    while True:
        code = get_random_string(length=10)
        res = User.objects.filter(invite_code=code)
        if len(res) > 0:
            continue
        else:
            break
    return code

class User(AbstractUser):
    nick_name = models.CharField(max_length=40,blank=True,null=True)
    signature = models.TextField(blank=True,null=True)
    subscriptes = models.ManyToManyField(Book,related_name='subscripte_books',null=True,blank=True)
    collections = models.ManyToManyField(Book,related_name='collection_books',null=True,blank=True)
    friends = models.ManyToManyField('User',related_name='user_friends',null=True,blank=True)
    avatar = models.OneToOneField(ImageWithThumb,on_delete=models.CASCADE,null=True,blank=True)
    vip = models.BooleanField(default=False,blank=False,null=False)
    vip_expire = models.DateTimeField(blank=True,null=True)
    # 每个月会重置的流量
    bandwidth_tmp = models.IntegerField(default=0,verbose_name='临时流量（每个月重置）')
    # 永久流量
    bandwidth_forever = models.IntegerField(default=0,verbose_name='永久流量')
    # vip流量
    bandwidth_vip = models.IntegerField(default=0, verbose_name='vip流量（有效期一个月）')
    bandwidth_used = models.PositiveIntegerField(default=0)
    bandwidth_remain =models.IntegerField(default=0)
    bandwidth_percent = models.PositiveIntegerField(default=100)
    kindle_email = models.EmailField(null=True,blank=True, unique=True, validators=[validate_email,])
    activate_token = models.CharField(default="",max_length=50,blank=True,null=True)
    activate_token_create_time = models.DateTimeField(null=True)
    inviter = models.ForeignKey("self",null=True,verbose_name='邀请者', on_delete=models.DO_NOTHING)
    invite_code = models.CharField(max_length=20)

    def get_bandwidth_total(self):
        return self.bandwidth_tmp + self.bandwidth_vip + self.bandwidth_forever

    def bandwidth_cost(self,volume,action,volume_type):
        """
        不管是不是vip之类的，直接传入信息到这个函数里，
        会自动判断vip，等。并自动记录下载记录，记录流量消费记录
        :param volume:
        :param action: 动作，push为推送，download为下载
        :param volume_type: download时，为VOLUME_TYPE_ZIP EPUB MOBI。推送时无需指定
        :return:
        """
        if self.vip:
            if self.have_cost_bandwidth_recently(volume):
                if action == 'download':
                    # 最近有消费过流量，所以不消费流量了，直接提供下载链接，并记录下载记录
                    record = DownloadRecord(user=self, volume=volume, info='No Cost',volume_type=volume_type,vip=self.vip)
                    record.save()
                    return {'status':BANDWIDTH_NO_COST}
            else:
                # 最近没有消费过流量，消费流量并记录
                volume_bandwidth = volume.get_volume_bandwidth_cost()
                if self.bandwidth_remain >= volume_bandwidth:
                    user_bandwidth_before = self.bandwidth_remain
                    self.bandwidth_used += volume_bandwidth
                    self.save()
                    download_cost_record = BandwidthCostRecord(user=self, volume=volume,
                                                               bandwidth_cost=volume_bandwidth,
                                                               user_bandwidth_before=user_bandwidth_before,
                                                               user_bandwidth_after=self.bandwidth_remain,
                                                               action='download',volume_type=volume_type)
                    download_cost_record.save()
                    record = DownloadRecord(user=self, volume=volume, info='cost',volume_type=volume_type,vip=self.vip)
                    record.save()
                    return {'status':BANDWIDTH_COST,'size':volume_bandwidth}
                else:
                    return {"status":BANDWIDTH_NOT_ENOUGH}
        else:
            # 免费用户下载所有资源都消耗对应体积的流量
            if volume_type == VOLUME_TYPE_ZIP: return {'status':ONLY_VIP}
            elif volume_type == VOLUME_TYPE_MOBI: volume_bandwidth = volume.mobi_file.size/1024.0/1024.0
            elif volume_type == VOLUME_TYPE_EPUB: volume_bandwidth = volume.epub_file.size/1024.0/1024.0
            else: return {"status":ERROR}
            # 如果是特别推荐里的书籍，流量消耗为0
            if len(HomePageSpecialSide.objects.filter(book=volume.book))>0: volume_bandwidth = 0
            # 检测下最近是否有下载过对应格式的卷，有下载过的话就不消耗流量
            res = self.have_cost_bandwidth_recently(volume,'download',volume_type)
            if res:
                record = DownloadRecord(user=self, volume=volume, info='no cost', volume_type=volume_type, vip=self.vip)
                record.save()
                return {"status": BANDWIDTH_NO_COST}
            else:
                # 检测剩余流量是否足够，不够返回error
                if self.bandwidth_remain <= volume_bandwidth: return {"status":BANDWIDTH_NOT_ENOUGH}
                # 流量足够的话消耗流量并记下流量消耗记录
                user_bandwidth_before = self.bandwidth_remain
                self.bandwidth_used += volume_bandwidth
                self.save()
                download_cost_record = BandwidthCostRecord(user=self, volume=volume,
                                                           bandwidth_cost=volume_bandwidth,
                                                           user_bandwidth_before=user_bandwidth_before,
                                                           user_bandwidth_after=self.bandwidth_remain,
                                                           action='download',
                                                           volume_type = volume_type)
                download_cost_record.save()
                record = DownloadRecord(user=self, volume=volume, info='cost', volume_type=volume_type,vip=self.vip)
                record.save()
                return {"status":BANDWIDTH_COST,'size':volume_bandwidth}








    def charge_bandwidth(self,charge_mode):
        if charge_mode == CHARGE_MODE_VIP:
            self.bandwidth_vip += self.bandwidth_vip + USER_BASE_BANDWIDTH + VIP_PLUS_BANDWIDTH
            self.vip = True
            self.vip_expire = now() + timedelta(days=30)
            if self.inviter is not None:
                # 有邀请者的话，每次氪金都给邀请者永久流量增加200M
                self.inviter.bandwidth_forever += 200
                self.inviter.save()
            self.save()

    def get_uer_bandwidth_records(self):
        records = BandwidthCostRecord.objects.filter(user=self).order_by('-cost_date')
        return records

    def add_bandwidth_cost(self,volume):
        """
        每当消费流量时，最好都用这个函数设置消费了的流量
        因为每次都会检测下剩余流量，以及最近有没有使用过流量，有的话就不消耗流量
        :return: False为流量不足，True为可以提供下载
        """
        time_threshold = now() - timedelta(hours=DOWNLOAD_LINK_AVAILABLE_HOURS)
        records = BandwidthCostRecord.objects.filter(user=self, volume=volume, cost_date__gt=time_threshold,action='download')
        if len(records)==0:
            volume_bandwidth = volume.get_volume_bandwidth_cost()
            if self.bandwidth_remain >= volume_bandwidth:
                user_bandwidth_before = self.bandwidth_remain
                self.bandwidth_used += volume_bandwidth
                self.save()
                file_download_record = BandwidthCostRecord(user=self, volume=volume, bandwidth_cost=volume_bandwidth,
                                                           user_bandwidth_before=user_bandwidth_before,
                                                           user_bandwidth_after=self.bandwidth_remain,
                                                           action='download')
                file_download_record.save()
                return True
            else:
                # 剩余流量不足，返回False
                return False
        else:
            return True

    def have_cost_bandwidth_recently(self,volume,action=None,volume_type=None):
        """
        检测最近几小时内是否有消耗过流量，消耗过了的话就返回True,否则False
        :return: False为没有消费过，True消费过
        """
        time_threshold = now() - timedelta(hours=DOWNLOAD_LINK_AVAILABLE_HOURS)
        if action is None:
            # push模式下获取最近所有的download push记录，如果有代表最近有消耗过流量
            records = BandwidthCostRecord.objects.filter(user=self, volume=volume,
                                                         cost_date__gt=time_threshold)
            if len(records) == 0: return False
            else: return True

        if volume_type is None:
            records = BandwidthCostRecord.objects.filter(user=self, volume=volume,
                                                        cost_date__gt=time_threshold, action=action)

        else:
            # volume_type的檢測是給免费用户用的，因为vip一本书扣除流量后都会开启下载
            records = BandwidthCostRecord.objects.filter(user=self, volume=volume,
                                                         cost_date__gt=time_threshold, action=action, volume_type=volume_type)
        if len(records) == 0:
            return False
        else:
            return True

    def save(self, *args, **kwargs):
        self.bandwidth_remain = self.get_bandwidth_total() - self.bandwidth_used
        if self.get_bandwidth_total() == 0:
            self.bandwidth_percent = 100
        else:
            p = int(self.bandwidth_remain*100.0/self.get_bandwidth_total())
            if p < 0: self.bandwidth_percent = 100
            else: self.bandwidth_percent = p

        super().save()

    def __str__(self):
        return self.username

    class Meta:
        verbose_name_plural = "用户"
        verbose_name = "用户"


class Comment(models.Model):
    book = models.ForeignKey(Book,on_delete=models.DO_NOTHING,verbose_name='关联书本')
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING,verbose_name='评论者')
    message = models.TextField(verbose_name='内容')
    comment_time = models.DateTimeField(default=now,verbose_name='评论时间')
    agree = models.PositiveIntegerField(default=0,verbose_name='赞人数')
    nouse = models.PositiveIntegerField(default=0,verbose_name='踩人数')

    def __str__(self):
        return self.message

    class Meta:
        verbose_name = "评论"
        verbose_name_plural = "评论"


class Score(models.Model):
    score = models.PositiveIntegerField(null=False, blank=False, verbose_name="分数")
    book = models.OneToOneField(Book,verbose_name='评分的书籍', on_delete=models.DO_NOTHING)
    user = models.OneToOneField(User,verbose_name='评分者', on_delete=models.DO_NOTHING)

    def __str__(self):
        return "%s %d %s" % (self.book.title, self.score, self.user.username)

    class Meta:
        verbose_name_plural = '评分'
        verbose_name = '评分'


# 原本这个类是放在mainsite app下的，但是放在mainsite下后因为引入了User，Account app也引入了Book
# 导致了循环import，出错，艹
class BandwidthCostRecord(models.Model):
    user = models.ForeignKey(User,on_delete=models.DO_NOTHING,verbose_name='用户')
    volume = models.ForeignKey(Volume,on_delete=models.DO_NOTHING,verbose_name='卷')
    volume_type = models.CharField(null=True,max_length=100,verbose_name='消耗的格式类型')
    cost_date = models.DateTimeField(default=now,verbose_name='消费日')
    # 下载消耗的流量，单位MB
    bandwidth_cost = models.IntegerField(null=False, blank=False,verbose_name='消费流量')
    user_bandwidth_before = models.IntegerField(null=False,blank=False,verbose_name='消费前剩余流量')
    user_bandwidth_after = models.IntegerField(null=False,blank=False,verbose_name='消费后剩余流量')
    # 是什么类型消费了流量，分为download和push
    action = models.CharField(max_length=20,null=False,blank=False,verbose_name='消耗类型')
    class Meta:
        verbose_name = '用户流量消费记录'
        verbose_name_plural = '用户流量消费记录'


class MailVertifySendRecord(models.Model):
    send_date = models.DateTimeField(default=now)
    # 重置密码的话，关联的uid
    relative_uid = models.IntegerField(null=True,verbose_name='重置密码uid')
    # activate为注册时激活账号， resetpwd 为重置密码
    type = models.CharField(max_length=20)
    token = models.CharField(max_length=50)
    # 注册时激活账号后，用来生成用户的用户名
    user_name = models.CharField(max_length=100,null=True)
    # 邮箱
    email = models.EmailField(null=True)
    password = models.CharField(max_length=255,null=True)
    who_inviter = models.ForeignKey(User,on_delete=models.DO_NOTHING,null=True,verbose_name='邀请者')


    class Meta:
        verbose_name_plural = '邮件验证发送列表'
        verbose_name = '邮件验证发送列表'


class PasswordResetMailSendRecord(models.Model):
    send_date = models.DateTimeField(default=now)
    # 重置密码的话，关联的uid
    user = models.ForeignKey(User,on_delete=models.DO_NOTHING)
    token = models.CharField(max_length=50)
    used = models.BooleanField(default=False)


    class Meta:
        verbose_name_plural = '密码重置邮件发送列表'
        verbose_name = '密码重置邮件发送列表'


class DownloadRecord(models.Model):
    user = models.ForeignKey(User,verbose_name='用户', on_delete=models.DO_NOTHING)
    volume = models.ForeignKey(Volume,verbose_name="卷名" , on_delete=models.DO_NOTHING)
    volume_type = models.CharField(null=False,verbose_name='下载哪个格式',max_length=100)
    download_date = models.DateTimeField(default=now, verbose_name='下载时间')
    info = models.CharField(max_length=100,verbose_name='信息')
    vip = models.BooleanField(null=False,verbose_name='创建时用户是否为vip')
    class Meta:
        verbose_name_plural = '用户下载记录'
        verbose_name = '用户下载记录'


class ChargeRecord(models.Model):
    user = models.ForeignKey( User, on_delete=models.DO_NOTHING,verbose_name='下订单用户')
    price = models.FloatField(verbose_name="价格")
    created_time = models.DateTimeField(default=now,verbose_name='创建订单的时间')
    payed_time = models.DateTimeField(null=True,verbose_name='付款成功时间')
    content = models.TextField(verbose_name="充值的注释")
    order_id = models.CharField(max_length=255,verbose_name='订单id')
    payed = models.BooleanField(default=False,verbose_name='付款是否成功')
    status = models.CharField(default='created',max_length=20)
    def set_payed(self):
        self.payed_time=now()
        self.payed=True
        self.save()

    class Meta:
        verbose_name = '充值记录'
        verbose_name_plural = '充值记录'


class AccountRegisterIpRecord(models.Model):
    ip = models.CharField(max_length=20,verbose_name='ip地址')
    reg_date = models.DateTimeField(default=now, verbose_name='请求时间')
    action = models.CharField(max_length=20, verbose_name='请求类型')


    class Meta:
        verbose_name = '注册ip记录'
        verbose_name_plural = '注册ip记录'


class UserFeedback(models.Model):
    email = models.CharField(max_length=255)
    message = models.TextField()
    user = models.ForeignKey(User,on_delete=models.DO_NOTHING,null=True)
    date = models.DateTimeField(default=now)
    ip = models.CharField(max_length=100)

    class Meta:
        verbose_name = '用户问题反馈'
        verbose_name_plural = '用户问题反馈'
