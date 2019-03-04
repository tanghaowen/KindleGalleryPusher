from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page,),
    path("<int:book_id>/", views.book_info, name="book_info"),
    path("<int:book_id>/getinfofrom/", views.get_info_from_online, name="book_info"),
]