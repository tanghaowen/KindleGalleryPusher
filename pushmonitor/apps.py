from django.apps import AppConfig
from .push_queue_monitor import *

class PushmonitorConfig(AppConfig):
    name = 'pushmonitor'
    verbose_name = '推送监控'
    run_already = False

    def ready(self):
        if not PushmonitorConfig.run_already:
            PushmonitorConfig.run_already = True
            self.monitor_thread = start_monitor_thread()