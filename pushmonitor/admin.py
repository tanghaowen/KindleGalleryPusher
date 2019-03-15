from django.contrib import admin
from .models import *
# Register your models here.

class PushQueueAdmin(admin.ModelAdmin):
    list_display = ['user','volume','status','added_date']

admin.site.register(PushQueue, PushQueueAdmin)