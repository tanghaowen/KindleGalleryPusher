import threading,time,os
from .mailsender import send_mail_use_smtp


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


# 这里写具体的push逻辑之类的
def push_function(tasks):
    recivers = []
    file_path = tasks[0].volume.mobi_push_file.path
    author_string = tasks[0].volume.book.get_authors_string()
    book_title = tasks[0].volume.book.title
    volume_name = tasks[0].volume.name
    file_name = "[%s] %s %s.mobi" % (author_string, book_title, volume_name)

    for task in tasks:
        recivers.append(task.user.kindle_email)


    print("开始推送 task_id: %d" % task.id)
    print("%s %s" % (task.volume.book.title,task.volume.name))
    print("文件路径:%s" % file_path)
    print("附件名:%s"%file_name)
    print("总共推送给%d人" % len(recivers))
    print(recivers)
    res = send_mail_use_smtp(recivers,file_path,file_name)
    if res:
        print("推送成功")
        task.status = "done"
        task.save()
        return True
    else:
        print("推送失败")
        task.status = 'error'
        task.save()
        return False


def start_monitor_thread():
    print("Now Start push monitor thread...")
    monitor_thread = PushMonitorThread()
    monitor_thread.daemon = True
    monitor_thread.start()
    print("monitor thread start ok")
    return monitor_thread


class PushMonitorThread(threading.Thread):
    def __init__(self):
        super().__init__()

    def init(self):
        from pushmonitor.models import PushQueue
        # 启动线程时检查下当前是否存在状态为doing的任
        # 有的话意味着这是上次意外退出只进行了一半的任务
        self.PushModels = __import__('pushmonitor.models', globals(), locals(), ['PushQueue'])
        self.error_terminated_tasks = self.PushModels.PushQueue.objects.filter(status='doing')
        if len(self.error_terminated_tasks):
            print("上次有意外终止的待推送，数量为%d 重启任务" % len(self.error_terminated_tasks))

    def run(self):
        time.time(10)
        self.init()
        while True:
            tasks = self.pop_push_task()
            if tasks is None:
                print("当前推送队列为空")
            else:
                print("开始推送")
                res = push_function(tasks)
                continue
            time.sleep(60)

    def pop_push_task(self):
        for task in self.error_terminated_tasks:
            if task.status == 'doing':
                print("上次有未完成的推送任务，将其设定为pending",task.id)
                task.status = 'pending'
                task.save()

        tasks = self.PushModels.PushQueue.objects.filter(status="pending")
        if len(tasks) == 0:
            print("当前推送队列为空")
            return None
        else:
            print("推送队列有任务...")
            task = tasks[0]
            volume_id = task.volume.id
            print("待推送的任务task id: %d  volume id: %d " %(task.id, volume_id))
            query_res = self.PushModels.PushQueue.objects.filter(volume__id = volume_id,status = 'pending')
            print("队列中包含同一volume的任务数量为%d" % (len(query_res)))
            for q in query_res:
                q.status = 'doing'
                q.save()
            return query_res




if __name__ == '__main__':
    start_monitor_thread()
