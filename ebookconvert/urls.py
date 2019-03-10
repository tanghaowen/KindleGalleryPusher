from django.contrib import admin
from django.urls import path
from . import views

app_name = "ebook_convert"
urlpatterns = [
    path('', views.convert_queue, name='convert_queue'),

]
