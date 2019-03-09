from django.db import models
from mainsite.models import *
from account.models import *
from django.dispatch import receiver
class PushQueue(models.Model):
    volume = models.ForeignKey(Volume, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    status = models.CharField(max_length=50)


def get_user_push_task_from_queue(user):
    tasks = PushQueue.objects.filter(user=user).order_by('-id')
    return tasks

def get_global_push_tasks_from_queue():
    tasks = PushQueue.objects.all().order_by('-id')
    return tasks

def task_already_in_push_queue(user, volume):
    """
    检测user和book的推送任务是否已经在推送队列内
    这里暂时用的是pushmonitor里的模型
    之后改成redis
    :param user:
    :param book:
    :return:
    """
    query_pending = PushQueue.objects.filter(user=user, volume=volume, status='pending')
    query_done = PushQueue.objects.filter(user=user, volume=volume, status='done')
    query_doing = PushQueue.objects.filter(user=user, volume=volume, status='doing')
    if len(query_pending)>0:
        return 'pending'
    if len(query_doing)>0:
        return 'doing'
    if len(query_done)>0:
        return 'done'
    return 'ok'


def put_task_to_push_queue(user, volume, force=False):
    """
    将user和volume插入到待推送队列中
    今后该用redis时要改写这部分
    :param user:
    :param volume:
    :return:
    """
    if user.kindle_email is not None and ('@kindle.' not in user.kindle_email):
        return 'no kindle email'
    volume_push_size = int(volume.mobi_push_file.size / 1024.0 / 1024.0)
    if (user.bandwidth_total - user.bandwidth_used) < volume_push_size:
        return 'bandwidth less'
    task_already_in_queue = task_already_in_push_queue(user,volume)
    if task_already_in_queue == 'pending':
        print("用户: %d %s %s 已经在待推送队列中" %(user.id, volume.book.title, volume.name))
        return 'pending'
    if task_already_in_queue == 'doing':
        print("用户: %d %s %s 正在推送" % (user.id, volume.book.title, volume.name))
        return 'doing'
    if task_already_in_queue == 'done':
        if not force:
            print("用户: %d %s %s 之前已经推送过" % (user.id, volume.book.title, volume.name))
            return 'done'
        else:
            queue = PushQueue(user=user, volume=volume, status='pending')
            queue.save()
            user.bandwidth_used += volume_push_size
            user.save()
            print("用户: %d %s %s 之前已经推送过" % (user.id, volume.book.title, volume.name))
            print("但因为force=True强制再次入队")
            return 'ok'
    else:
        print("用户: %d %s %s 未在推送队列中，推送任务入队" % (user.id, volume.book.title, volume.name))
        queue = PushQueue(user=user, volume=volume, status='pending')
        queue.save()
        user.bandwidth_used += volume_push_size
        user.save()
        # TODO: 在这里通知推送队列有新的书籍
        return 'ok'


@receiver(new_volume_showed_signal, sender= EbookConvertQueue, dispatch_uid='new_volume_showed_signal_reciver')
def new_volume_showed(sender, **kwargs):
    print("有新的volume转换完毕，show=True")
    volume = kwargs['volume']
    print(volume.book.title)
    print(volume.name)
    print("开始获取此volume对应的book的订阅用户")
    volume_push_size = int(volume.mobi_push_file.size/1024.0/1024.0)
    book_subscripte_users = volume.book.subscripte_books.all().filter(kindle_email__contains="@kindle.", bandwidth_remain__gte=volume_push_size)
    for user in book_subscripte_users:
        print("用户：", user.username)
        res = put_task_to_push_queue(user,volume)


