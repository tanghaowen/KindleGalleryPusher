from django.contrib import admin
from django.urls import path
from . import views

app_name = "account"
urlpatterns = [
    path('login/', views.account_login, name='login'),
    path('register/',views.account_register, name='register'),
    path('logout/',views.account_logout, name='logout'),
    path('user/', views.set_self_account, name='self_profile'),
    path('user/profile', views.set_profile, name='set_profile'),
    path('user/<int:uid>/', views.account_profile, name='other_profile'),
    path('user/queue/', views.push_queue, name='push_queue'),

]
