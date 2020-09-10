from django.urls import re_path
from .views import *

urlpatterns = [
    # 用户重复注册
    re_path(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', UsernameCountView.as_view()),
    # 手机号重复注册
    # re_path(r'^/mobiles/(?P<mobile>1[3-9]\d{9})/count/$', MobileCountView.as_view()),
    re_path(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', MobileCountView.as_view()),
]
