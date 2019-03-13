from django.contrib import admin
from django.urls import path
from . import views

app_name = "account"
urlpatterns = [
    path('login/', views.account_login, name='login'),
    path('register/',views.account_register, name='register'),
    path('forgot/',views.account_reset_password, name='forgot'),
    path('resetpsw/',views.rest_password, name='reset_password'),
    path('active/',views.account_activate, name='active'),
    path('logout/',views.account_logout, name='logout'),
    path('user/', views.set_self_account, name='self_profile'),
    path('user/profile', views.set_profile, name='set_profile'),
    path('user/<int:uid>/', views.account_profile, name='other_profile'),
    path('user/queue/', views.push_queue, name='push_queue'),
    path('charge/', views.kakin, name='charge'),
    path('payoknDxx4S0qCf/', views.payok, name='pay_ok'),
    path('precharge/', views.precharge, name='precharge'),
    path('records/', views.bandwidth_cost_records, name='bandwidth_records'),


]
