"""KindleComicPusher URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from mainsite.views import home_page, volume_download, show_bandwidth_rule, feedback
from ebookconvert.views import convert_queue
from django.conf import settings
from django.conf.urls import include, url  # For django versions before 2.0
from django.urls import include, path  # For django versions from 2.0 and up


urlpatterns = [
    path("",home_page,name='home_page'),
    path('rule/', show_bandwidth_rule, name='bandwidth_rule'),
    path("book/", include("mainsite.urls")),
    path("feedback/", feedback, name='feedback' ),
    path("download/",volume_download, name='volume_download'),
    path('accounts/', include('account.urls')),
    path('search/', include('mainsite.urls_search')),
    path('pushtask/',include('pushmonitor.urls')),
    path('converts/',convert_queue,name='convert_queue'),
    path('admin/', admin.site.urls),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)