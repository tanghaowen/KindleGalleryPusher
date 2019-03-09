from django.apps import AppConfig
from .queue_monitor import *


class EbookconvertConfig(AppConfig):
    verbose_name = '书籍格式转换队列'
    name = 'ebookconvert'
    run_already = False

    def ready(self):
        if not EbookconvertConfig.run_already:
            EbookconvertConfig.run_already = True
            self.monitor_thread = start_monitor_thread()

