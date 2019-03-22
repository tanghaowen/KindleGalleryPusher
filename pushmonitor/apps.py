from django.apps import AppConfig
from .push_queue_monitor import *


class PushmonitorConfig(AppConfig):
    name = 'pushmonitor'
    verbose_name = 'push monitor'
    run_already = False

    # djangoが起動する時、自動にpush monitor threadをスタート
    def ready(self):
        if not PushmonitorConfig.run_already:
            PushmonitorConfig.run_already = True
            self.monitor_thread = start_monitor_thread()
