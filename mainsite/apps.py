from django.apps import AppConfig
from suit.apps import DjangoSuitConfig


class MainsiteConfig(AppConfig):
    name = 'mainsite'
    verbose_name = 'mainsite'


class SuitConfig(DjangoSuitConfig):
    layout = 'horizontal'
