from django.urls import re_path
from .views import *

urlpatterns = [
    # 获取 QQ 扫码登录链接
    re_path(r'^qq/authorization/$', QQFirstView.as_view()),
    # QQ用户部分接口:
    re_path(r'^oauth_callback/$', QQUserView.as_view()),
]