from django.contrib import admin
from django.urls import path
from . import views

app_name = 'search_site'
urlpatterns = [
    path('', views.search_page,name='search_page'),
]