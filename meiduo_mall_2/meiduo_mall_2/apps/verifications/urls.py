from django.urls import re_path
from .views import *

urlpatterns = [

    re_path(r'^image_codes/(?P<uuid>[\w-]+)/$', ImageCodeView.as_view()),

]