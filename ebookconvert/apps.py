from django.apps import AppConfig
from .queue_monitor import *

class EbookconvertConfig(AppConfig):
    name = 'ebookconvert'
    run_already = False

    def ready(self):
        if not self.run_already:
            self.run_already = True
            self.monitor_thread = start_monitor_thread()

