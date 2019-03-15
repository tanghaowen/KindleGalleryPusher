from django.db import models
from mainsite.models import *
from account.models import *
from django.dispatch import receiver
class PushQueue(models.Model):
    volume = models.ForeignKey(Volume, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    status = models.CharField(max_length=50)
    added_date = models.DateTimeField(default=now)


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
    return 'note exits'


def put_task_to_push_queue(user, volume, force=False, ignore_bandwidth = False):
    """
    将user和volume插入到待推送队列中
    今后改用redis时要改写这部分
    :param user:
    :param volume:
    :param force:
    :param ignore_bandwidth: 被动订阅推送因为不消耗流量，所以这个是用来被动订阅推送的
    :return:
    """
    # 检测kindle邮箱是否设置完成
    if user.kindle_email is None or ('@kindle.' not in user.kindle_email):
        return 'no kindle email'
    volume_push_size = int(volume.mobi_push_file.size / 1024.0 / 1024.0)
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

    # 被动订阅推送因为不消耗流量，所以检测到之后直接推入队内
    if ignore_bandwidth:
        print("因为为被动推送，不消耗流量")
        record = BandwidthCostRecord(user=user, volume=volume, bandwidth_cost=volume_push_size,
                                     user_bandwidth_before=user.bandwidth_remain,
                                     user_bandwidth_after=user.bandwidth_remain,
                                     action='subsc push')
        record.save()
        queue = PushQueue(user=user, volume=volume, status='pending')
        queue.save()

        return 'ok'

    # 这里的是之前没有推送过，或者推送过后依旧设置force的
    if user.vip:
        # vip因为扣除流量后所有推送下载都免费，这里传入push会自动检测最近的push和download记录
        res = user.have_cost_bandwidth_recently(volume=volume)
        if res:
            print("用户: %d %s %s 为vip未在推送队列中，最近花费过流量，无流量消耗推送任务入队" % (user.id, volume.book.title, volume.name))
            queue = PushQueue(user=user, volume=volume, status='pending')
            queue.save()
            return 'ok'
        else:
            print("用户: %d %s %s 为vip未在推送队列中，最近没有花费过流量，消耗后推送任务入队" % (user.id, volume.book.title, volume.name))
            if (user.bandwidth_total - user.bandwidth_used) < volume_push_size:
                print('流量不够')
                return 'bandwidth less'
            user_bandwidth_before = user.bandwidth_remain
            user.bandwidth_used += volume_push_size
            user.save()
            record = BandwidthCostRecord(user=user,volume=volume,bandwidth_cost=volume_push_size,
                                user_bandwidth_before=user_bandwidth_before,
                                user_bandwidth_after = user.bandwidth_remain,
                                action='push')
            record.save()
            queue = PushQueue(user=user, volume=volume, status='pending')
            queue.save()
            return 'ok'
    else:
        # 非vip每次推送都要消耗流量
        print("用户: %d %s %s 为非vip未在推送队列中，消耗流量。" % (user.id, volume.book.title, volume.name))
        if (user.bandwidth_total - user.bandwidth_used) < volume_push_size:
            print('流量不够')
            return 'bandwidth less'
        user_bandwidth_before = user.bandwidth_remain
        user.bandwidth_used += volume_push_size
        user.save()
        record = BandwidthCostRecord(user=user, volume=volume, bandwidth_cost=volume_push_size,
                                     user_bandwidth_before=user_bandwidth_before,
                                     user_bandwidth_after=user.bandwidth_remain,
                                     action='push')
        record.save()
        queue = PushQueue(user=user, volume=volume, status='pending')
        queue.save()
        return 'ok'



@receiver(new_volume_showed_signal, sender= EbookConvertQueue, dispatch_uid='new_volume_showed_signal_reciver')
def new_volume_showed(sender, **kwargs):
    print("有新的volume转换完毕，show=True")
    volume = kwargs['volume']
    print(volume.book.title)
    print(volume.name)
    print("开始获取此volume对应的book的订阅用户")
    volume_push_size = int(volume.mobi_push_file.size/1024.0/1024.0)
    # 被动推送时，不消耗流量
    # TODO: 或者消耗流量只为1/10？
    # book_subscripte_users = volume.book.subscripte_books.all().filter(kindle_email__contains="@kindle.", bandwidth_remain__gte=volume_push_size)
    book_subscripte_users = volume.book.subscripte_books.all().filter(kindle_email__contains="@kindle.")
    for user in book_subscripte_users:
        print("用户：", user.username)
        res = put_task_to_push_queue(user,volume,ignore_bandwidth=True)


