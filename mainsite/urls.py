from django.contrib import admin
from django.urls import path
from . import views

app_name = 'main_site'
urlpatterns = [
    path('', views.home_page,name='home_page'),
    path("<int:book_id>/", views.book_info, name="book"),
    path("<int:book_id>/getinfofrom/", views.get_info_from_online, name="book_info"),
    path("<int:book_id>/subsc/",views.book_subscribe, name='book_subscribe'),
    path("<int:book_id>/collect/", views.book_collect, name='book_collect'),
    path("<int:book_id>/comment/", views.book_comment, name='book_comment'),
    path("<int:book_id>/score/", views.book_score, name='book_score'),
    path("<int:book_id>/push/", views.book_push, name='book_push'),
    path("<int:book_id>/upload/", views.upload_file, name='book_upload'),
    path("recently/", views.full_recently_updated_books, name='book_recently'),
]