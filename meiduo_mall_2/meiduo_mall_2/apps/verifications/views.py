from django.http import HttpResponse
from django.views import View
from meiduo_mall_2.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import JsonResponse

class ImageCodeView(View):
    def get(self,request,uuid):
        # 借助captcha 工具生成图形验证码
        text,image = captcha.generate_captcha()
        print(text)
        # 链接Redis数据库
        redis_conn = get_redis_connection('verify_code')
        # 利用链接对象,保存数据到redis数据库,使用setex函数
        # redis_conn.setex(key,expire,value)
        redis_conn.setex('img_%s'%uuid,300,text)

        # 返回图片
        return HttpResponse(image,content_type='image/jpg')

class MobileCodeView(View):
    def get(self,request,mobile):
        # 提取参数
        image_code_client = request.get("image_code")
        uuid = request.get('image_code_id')
        # 校验参数
        if not all(['image_code','uuid']):
            return JsonResponse({
                'code':400,
                'errmsg':"缺少必要参数"
            })
        # 创建链接redis的对象
        redis_conn = get_redis_connection('verify_code')

        # 提取图形验证码
        redis_image_code = redis_conn.get('img_%s'%uuid)

        # 参数校验
        if redis_image_code is None:
            return HttpResponse({
                'code':400,
                'errmsg':"验证码已过期",
            },status=400)
        # 避免恶意测试验证码,删除
        redis_image_code = redis_image_code.decode()
        redis_conn.delete('img_%s'%uuid)

        # 比对(忽略大小写)
        if image_code_client.lower() != redis_image_code.lower():
            return HttpResponse({
                'code':400,
                'errmsg':"验证码输入错误"
            },status=400)

        # 发送短信验证码
        conn = get_redis_connection('sms_code')