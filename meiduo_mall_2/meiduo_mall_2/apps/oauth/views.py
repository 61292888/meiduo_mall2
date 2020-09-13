from django.contrib.auth import login
from django.http import JsonResponse
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from meiduo_mall_2.settings import dev
from .models import OAuthQQUser
import logging,json,re
from itsdangerous import TimedJSONWebSignatureSerializer
from django_redis import get_redis_connection
from itsdangerous import BadData
from users.models import User

def generate_access_token(openid):
    """ 对传入的openid进行加密处理,返回token """
    # QQ 登录保存用户数据的 token 有效期
    # settings.SECRET_KEY: 加密使用的秘钥
    # 过期时间: 600s = 10min
    serializer = TimedJSONWebSignatureSerializer(dev.SECRET_KEY,expires_in=600)
    data = {"openid":openid}  # 当前格式是字典
    # print("data的格式是:",type(data))
    # 对data进行加密处理
    token = serializer.dumps(data)  # 当前加密成二进制格式
    # print("token的格式是:",type(token))
    # 加密后解码返回
     # 前端指定接收字符串,所以解码成字符串返回
    return token.decode()

# 定义函数, 检验传入的 access_token 里面是否包含有 openid
def check_access_token(access_token):
    """
    :param access_token: token
    :return: openid or None
    """
    # 调用itsdangerous中的类,生成对象
    serializer = TimedJSONWebSignatureSerializer(dev.SECRET_KEY,expires_in=600)
    try:
        """ 对传入的openid进行加密处理,返回token """
        # QQ 登录保存用户数据的 token 有效期
        # settings.SECRET_KEY: 加密使用的秘钥
        # 过期时间: 600s = 10min
        data = serializer.loads(access_token)
    except BadData:
        # 如果获取不到就返回None,因为出错就不是我们认可的
        return None
    return data.get('openid')


# 获取QQ登录的扫码界面
class QQFirstView(View):
    def get(self,request):
        # next 表示从哪个页面进入到的登录页面,登陆后还回到原来的界面
        next = request.GET.get('next')

        # 获取QQ登录界面
        # 我们申请的 客户端id:client_id=dev.QQ_CLIENT_ID
        # 我们申请的 客户端秘钥:client_secret=dev.QQ_CLIENT_SECRET
        # 我们申请时添加的: 登录成功后回调的路径:redirect_uri=dev.QQ_REDIRECT_URI
        oauth = OAuthQQ(client_id=dev.QQ_CLIENT_ID,
                        client_secret=dev.QQ_CLIENT_SECRET,
                        redirect_uri=dev.QQ_REDIRECT_URI,
                        state=next)
        login_url = oauth.get_qq_url()

        return JsonResponse({
            'code':0,
            'errmsg':"OK",
            'login_url':login_url
        })

class QQUserView(View):
    """
    用户扫码登录回调处理
    """
    def get(self,request):
        # oauch 2.0认证
        # 获取前端传递的参数
        code = request.GET.get('code')
        # 校验参数
        if not code:
            return JsonResponse({"code":400,"errmsg":'缺少必要参数'})


        # 创建工具对象
        oauth = OAuthQQ(client_id=dev.QQ_CLIENT_ID,
                        client_secret=dev.QQ_CLIENT_SECRET,
                        redirect_uri=dev.QQ_REDIRECT_URI)

        try:
            # 利用工具携带code向QQ服务器请求access_token
            access_token = oauth.get_access_token(code)
            # 利用工具携带acc_token向QQ服务器请求openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            # 如果出错就写入日志
            logging.error(e)
            return  JsonResponse({
                'code':400,
                'errmsg':'oauth 2.0认证失败'
            })

        try:
            # 尝试通过获取判断是否已存在openid
            oauth = OAuthQQUser.objects.get(openid=openid)
        except  OAuthQQUser.DoesNotExist as e:
            # 4、用户没有绑定过qq：我们需要返回加密的openid
            # 调用我们自定义的方法, 对 openid 进行加密
            # 把 openid 变为 access_token
            access_token = generate_access_token(openid)
            return JsonResponse({
                'code':300,'errmsg':"ok",
                'access_token':access_token
            })

        # 5、用户已经绑定过qq——登陆成功！！
        user = oauth.user
        login(request, user) # 状态保持
        response = JsonResponse({'code':0, 'errmsg': 'ok'})
        response.set_cookie('username', user.username, max_age=3600*24*14)
        return response

    def post(self,request):
        # 获取全部参数
        data = json.loads(request.body.decode())
        mobile =data.get("mobile")
        password= data.get("password")
        sms_code = data.get('sms_code')
        access_token = data.get('access_token')
        # 校验全部参数,是否齐全
        if not all([mobile,password,sms_code,access_token]):
            return JsonResponse({'code':400,'errmsg':'缺少必要参数'})
        # 校验手机号是否合法
        if not re.match(r"^1[3-9]\d{9}$",mobile):
            return JsonResponse({'code':400,"errmsg":"请输入正确的手机号"})
        # 校验密码是否合格
        if not re.match(r"^[a-zA-Z0-9]\d{8,20}$",password):
            return JsonResponse({"code":400,'errmsg':"请输入8-20位密码"})
        # 校验短信验证码是否一致
        # 创建链接数据库工具对象
        conn = get_redis_connection('sms_code')
        # 获取验证码
        sms_code_redis = conn.get('sms_%s'%mobile)
        # 校验验证码是否存在
        if not sms_code_redis:
            return JsonResponse({'code':400,'errmsg':"验证码已过期"})
        # 校验验证码是否与输入匹配
        if  sms_code_redis.decode() != sms_code :
           return JsonResponse({'code':400,'errmsg':"验证码输入有误"})

        # 调用自定的函数校验openid
        openid = check_access_token(access_token) 
        # 判断是否存在
        if not openid:
            return JsonResponse({"code":400,"errmsg":"缺少openid"})

        # 如果获取用户通过
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist as e:
            # 如果出错就是没有用户,则新建
            user = User.objects.create_user(username=mobile,
                                            password=password,mobile=mobile)
        # else:
        #     # 校验一下用户是否存在,及校验密码
        #     if not user.check_password(password):
        #         return JsonResponse({
        #             "code":400,"errmsg":"输入密码不正确"
        #         })

        # 绑定用户
        try:
            OAuthQQUser.objects.create(openid=openid,user=user)
        except Exception as e:
            return JsonResponse({'code':400,"errmsg":"往数据库写入数据错误"})
        # 状态保持
        login(request,user)
        # 创建响应对象
        response = JsonResponse({"code":0,'errmsg':"OK"})
        # 返回时设置保存到cookie,有效期14天
        response.set_cookie("username",user.username,max_age=3600*24*14)
        # 响应
        return response
