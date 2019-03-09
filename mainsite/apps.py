from django.apps import AppConfig
from suit.apps import DjangoSuitConfig


class MainsiteConfig(AppConfig):
    name = 'mainsite'
    verbose_name = '主站'


class SuitConfig(DjangoSuitConfig):
    layout = 'horizontal'
