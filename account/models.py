from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
from mainsite.models import  *
from django.utils.timezone import now
from django.core.validators import validate_email


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
