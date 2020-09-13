from django.contrib.auth.backends import ModelBackend
import re
from .models import User

def get_user_by_account(account):
    " 判断account是否是手机号,返回user对象"
    try:
        # 正则判断是不是手机号
        if re.match("^1[3-9]\d{9}",account):
            # 条件满足则通过模型类获取用户对象
            user = User.objects.get(mobile=account)
        else:
            # 如果是用户名,也获取用户对象
            user = User.objects.get(username=account)
    # 如果上述条件都不满足则报错
    except Exception as e:
        # 并返回None
        return None
    else:
        # 如果得到user就返回用户对象
        return user

class UsernameMobileAuthBackend(ModelBackend):
    # 自定义用户后端
    def authenticate(self,request,username=None,password=None,**kwargs):
        """
        :param request:
        :param username:
        :param password:
        :param kwargs:
        :return:
        """
        # 用自定义的函数(判断用户名还是手机号还是用户名的那个)
        user = get_user_by_account(username)

        # 校验用户名是否存在及用户名密码是否正确
        if user and user.check_password(password):
            # 如果正确就返回
            return user

