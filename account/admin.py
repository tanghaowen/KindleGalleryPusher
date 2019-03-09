from django.contrib import admin
from account.models import *
# Register your models here.


class SubscInline(admin.TabularInline):
    model = User.subscriptes.through


class CollInline(admin.TabularInline):
    model = User.collections.through


class UserAdmin(admin.ModelAdmin):
    filter_vertical = ['subscriptes','collections']


admin.site.register(User, UserAdmin)
admin.site.register(Comment)
admin.site.register(Score)