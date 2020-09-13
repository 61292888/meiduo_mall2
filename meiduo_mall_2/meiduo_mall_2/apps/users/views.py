import json
import re
from django.http import JsonResponse
from django.views import View
from users.models import User
from django_redis import get_redis_connection
from django.contrib.auth import login,authenticate,logout

# 用户名重复注册
class UsernameCountView(View):
    def get(self,request,username):

        # 从model.User模型类中获取对象,filter筛选出所有符合条件的内容,count统计获取到的个数
        try:
            count = User.objects.filter(username=username).count()
            print('当前用户名已存在:',count)
        except Exception as e:
            return JsonResponse({
                "code": 400,
                "errmsg":"访问数据库失败",
            })

        return JsonResponse({
            'code':200,
            'errmsg':'ok',
            'count':count}
            )

#手机号重复注册
class MobileCountView(View):
    def get(self,request,mobile):
        try:
            count = User.objects.filter(mobile=mobile).count()
            print('当前手机号已存在:',count)
        except Exception as e:
            return JsonResponse({
                'code':400,
                'errmsg':'数据库访问失败'
            })
        return JsonResponse({
            'code':0,
            'errmsg':'OK',
            'count':count,
        })

#用户注册
class RegisterView(View):
    def post(self,request):
#         # 接受参数,保存到数据库
        data = json.loads(request.body.decode())
        username = data.get('username')
        password = data.get('password')
        password2 = data.get('password2')
        mobile = data.get('mobile')
        allow = data.get('allow')
        sms_code = data.get('sms_code')
        # 校验参数是否完全输入
        if not all([username,password,password2,mobile,allow,sms_code]):
            return JsonResponse({'code':400,'errmsg':'缺少必要参数',},status=401)

        # 对接收到的参数一一校验
        # 校验用户名
        if not re.match(r"^\w{5,20}$",username):
            return JsonResponse({'code': 400,'errmsg': '用户名格式错误',}, status=401)
        if not re.match(r"^\w{8,20}$",password):
            return JsonResponse({'code': 400,'errmsg': '密码格式错误',}, status=401)

        if password2 != password :
            return JsonResponse({'code': 400,'errmsg': '两次输入的密码不一致',}, status=401)

        if not allow:

            return JsonResponse({'code': 400,'errmsg': '未勾选协议',}, status=401)

        if not re.match(r"^\d{6}$",sms_code):
            return JsonResponse({'code':400,'errmsg':"短信验证码输入有误"})



        # 验证短信
        # 链接数据库#
        # 获取短信验证码
        conn = get_redis_connection("sms_code")
        sms_code_redis = conn.get('sms_%s'%mobile)

        if not sms_code_redis:
            return JsonResponse({'code':400,'errmsg':'短信验证码已过期'},status=401)
        sms_code_redis = sms_code_redis.decode()
        if sms_code_redis != sms_code:
            return JsonResponse({'code':400,'errmsg':'短信验证码有误'},status=401)

        # 讲接收到的参数保存到数据库
        # User.objects.create() --> 构建的用户模型类对象，密码不会加密
        # User.objects.create_user() --> 构建用户模型类对象，把明文密码加密
        # User.objects.create_superuser() --> 构建用户模型类对象，把明文密码加密以及is_staff=True
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                mobile = mobile
            )
        except Exception as e:
            return JsonResponse({'code':400,"errmsg":'保存到数据库错误'})

        # 添加如下代码
        login(request,user)
        response = JsonResponse({'code':0,'errmsg':"OK"})
        # 实现状态保持
        response.set_cookie('username',user.username,max_age=3600*24*14)
        # 返回
        return response

class LoginView(View):
    def post(self,request):
        # 接收参数
        data = json.loads(request.body.decode())
        username =data.get('username')
        password = data.get('password')
        remembered = data.get('remembered')

        # 校验参数
        if not all([username,password]):
            return JsonResponse({'code':400,'errmsg':'缺少必要参数'})
        if not re.match(r'^\w{5,20}$', username):
            return JsonResponse({'code':400, 'errmsg': '用户名格式有误'}, status=400)

        if not re.match(r'^\w{8,20}$', password):
            return JsonResponse({'code':400, 'errmsg': '密码格式有误'}, status=400)

        # user = authenticate(request,username=username,password=password)
        user = authenticate(request, username=username, password=password)
        if not user:
            return  JsonResponse({'code':400,"errmsg":"当前身份信息验证有误"})

        # 状态保持
        login(request,user)

        # 设置密码记住模式
        if not remembered:
            # 设置0,表示关闭浏览器清除session
            request.session.set_expiry(0)
        else:
            # 设置默认session有效期两周
            request.session.set_expiry(None)

        print("用户信息:",user)

        # 构建响应
        response = JsonResponse({'code':0,'errmsg':"ok"})
        response.set_cookie('username',user.username,max_age=3600*24*14)
        return response

class LogoutView(View):
    def delete(self,request):
        # 清理session
        logout(request)

        response = JsonResponse({"code":0,'errmsg':'ok'})
        # 调用对象清理Cookie
        response.delete_cookie("username")
        return response