from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
from django.utils.crypto import get_random_string

from mainsite.models import *
from django.utils.timezone import now, timedelta
from django.core.validators import validate_email


DOWNLOAD_LINK_AVAILABLE_HOURS = 1
ACCOUNT_ACTIVATE_TOKEN_AVAILABLE_HOURS = 1

class User(AbstractUser):
    nick_name = models.CharField(max_length=40,blank=True,null=True)
    signature = models.TextField(blank=True,null=True)
    subscriptes = models.ManyToManyField(Book,related_name='subscripte_books',null=True,blank=True)
    collections = models.ManyToManyField(Book,related_name='collection_books',null=True,blank=True)
    friends = models.ManyToManyField('User',related_name='user_friends',null=True,blank=True)
    avatar = models.OneToOneField(ImageWithThumb,on_delete=models.CASCADE,null=True,blank=True)
    vip = models.BooleanField(default=False,blank=False,null=False)
    vip_expire = models.DateTimeField(blank=True,null=True)
    bandwidth_total = models.IntegerField(default=0)
    bandwidth_used = models.PositiveIntegerField(default=0)
    bandwidth_remain =models.IntegerField(default=0)
    bandwidth_percent = models.PositiveIntegerField(default=100)
    kindle_email = models.EmailField(null=True,blank=True, unique=True, validators=[validate_email,])
    activate_token = models.CharField(default="",max_length=50,blank=True,null=True)
    activate_token_create_time = models.DateTimeField(null=True)

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

    def have_cost_bandwidth_recently(self,volume):
        """
        检测最近几小时内是否有消耗过流量，消耗过了的话就返回True,否则False
        :return: False为流量不足，True为可以提供下载
        """
        time_threshold = now() - timedelta(hours=DOWNLOAD_LINK_AVAILABLE_HOURS)
        records = BandwidthCostRecord.objects.filter(user=self, volume=volume,
                                                     cost_date__gt=time_threshold, action='download')
        if len(records) == 0:
            return False
        else:
            return True

    def save(self, *args, **kwargs):
        if self.bandwidth_total == 0:
            self.bandwidth_percent = 100
        else:
            p = int(self.bandwidth_remain*100.0/self.bandwidth_total)
            if p < 0: self.bandwidth_percent = 100
            else: self.bandwidth_percent = p
        self.bandwidth_remain = self.bandwidth_total - self.bandwidth_used
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
    relative_uid = models.IntegerField(null=True)
    # activate为注册时激活账号， resetpwd 为重置密码
    type = models.CharField(max_length=20)
    token = models.CharField(max_length=50)
    # 注册时激活账号后，用来生成用户的用户名
    user_name = models.CharField(max_length=100,null=True)
    # 邮箱
    email = models.EmailField(null=True)
    password = models.CharField(max_length=255,null=True)


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