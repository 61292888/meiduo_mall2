# import random
# import re
# from django.http import HttpResponse
# from django.views import View
# from meiduo_mall_2.libs.captcha.captcha import captcha
# from django_redis import get_redis_connection
# from django.http import JsonResponse
# from meiduo_mall_2.libs.yuntongxun.yuntongxun.ccp_sms import CCP
# from celery_tasks.sms.tasks import ccp_send_sms_code
#
# class ImageCodeView(View):
#     def get(self,request,uuid):
#         # 借助captcha 工具生成图形验证码
#         text,image = captcha.generate_captcha()
#         print(text)
#         # 链接Redis数据库
#         redis_conn = get_redis_connection('verify_code')
#         # 利用链接对象,保存数据到redis数据库,使用setex函数
#         # redis_conn.setex(key,expire,value)
#         redis_conn.setex('img_%s'%uuid,300,text)
#
#         # 返回图片
#         return HttpResponse(image,content_type='image/jpg')
#
# class MobileCodeView(View):
#     def get(self,request,mobile):
#
#         # 创建链接redis的对象
#         redis_conn = get_redis_connection('sms_code')
#         # 校验redis中是否存在防止恶意校验的验证码标记
#         send_flag = redis_conn.get('send_flag_%s'%mobile)
#         # 判断是否存在
#         if send_flag:
#             return JsonResponse({
#                 'code':400,
#                 'errmsg':'发送短信过于频繁'
#             },status=401)
#         # 提取参数
#         image_code_client = request.GET.get("image_code")
#         uuid = request.GET.get('image_code_id')
#         # 校验参数
#         if not all(['image_code','uuid']):
#             return JsonResponse({
#                 'code':400,
#                 'errmsg':"缺少必要参数"
#             })
#
#         # 提取图形验证码
#         redis_image_code = redis_conn.get('img_%s'%uuid)
#
#         # 参数校验
#         if redis_image_code is None:
#             return HttpResponse({
#                 'code':400,
#                 'errmsg':"验证码已过期",
#             },status=400)
#         # 避免恶意测试验证码,删除
#         redis_conn.delete('img_%s'%uuid)
#         redis_image_code = redis_image_code.decode()
#
#         # 比对(忽略大小写)
#         if image_code_client.lower() != redis_image_code.lower():
#             return HttpResponse({
#                 'code':400,
#                 'errmsg':"验证码输入错误"
#             },status=400)
#
#         # 构建短信验证码
#         sms_code = '%06d'% random.randint(100000,999999)
#         print('当前手机验证码为:',sms_code)
#
#         # 创建管道对象
#         p1 = redis_conn.pipeline()
#         # 保存验证码到redis数据库:依旧使用setex,有效期300秒
#         # sms_%s 拼接短信验证码存入数据库,验证码300秒有效
#         # redis_conn.setex('sms_%s'%mobile,300,sms_code)
#         p1.setex('sms_%s'%mobile,300,sms_code)
#         # 将结果独立保存一份作为开头校验,防止恶意频繁发送验证码
#         # redis_conn.setex('send_flag_%s',60,1)
#         p1.setex('send_flag_%s'%mobile,60,1)
#         # 执行管道
#         p1.execute()
#
#         # 发送验证码 保持五分钟
#         # CCP().send_template_sms(mobile,[sms_code,5],1)
#         # 调用异步任务发送短信
#         ccp_send_sms_code.delay(mobile,sms_code)
#
#         # 返回
#         return HttpResponse({
#             'code':200,
#             'errmsg':'短信发送成功'
#         })
#


from django.shortcuts import render
from django.views import View
from django.http import HttpResponse,JsonResponse
# get_redis_connection: 一个函数，该函数可以根据django的配置直接获取redis连接
from django_redis import get_redis_connection
import random
from meiduo_mall_2.libs.captcha.captcha import captcha
# from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from celery_tasks.sms.tasks import ccp_send_sms_code
# Create your views here.

import logging
logger = logging.getLogger('django')

# 图形验证码接口
class ImageCodeView(View):

    def get(self, request, uuid):

        # 1、调用库生成图形验证码
        text, image = captcha.generate_captcha()
        print(text)
        # 2、存储redis
        conn = get_redis_connection('verify_code')

        try:
            # 验证码写入redis
            conn.setex(
                "img_%s"%uuid,
                300,
                text
            )
        except Exception as e:
            print(e)
            logger.error(e)

        # 3、构建响应
        return HttpResponse(image, content_type='image/jpg')

import re
# 短信验证码接口
class SMSCodeView(View):

    def get(self, request, mobile):

        # 1、提取参数
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 2、校验参数
        if not all([image_code, uuid]):
            return JsonResponse({
                'code': 400,
                'errmsg': '缺少必要参数'
            }, status=400)
        if not re.match(r'^\w{4}$', image_code):
            return JsonResponse({
                'code': 400,
                'errmsg': '图片验证码格式不符'
            }, status=400)
        if not re.match(r'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$', uuid):
            return JsonResponse({
                'code': 400,
                'errmsg': 'uuid格式不符'
            }, status=400)

        # 3、校验redis中的图片验证码是否一致——业务层面上的校验
        conn = get_redis_connection('verify_code')
        # 3.1 提取redis中存储的图片验证码
        # get(): b"YBCF"
        image_code_from_redis = conn.get("img_%s"%uuid)

        # 如果从redis中读出的验证码是空；
        if not image_code_from_redis:
            return JsonResponse({'code':400, 'errmsg': '验证码过期'}, status=400)
        # 如果读出来的不是空，我们要删除该验证码
        image_code_from_redis = image_code_from_redis.decode()
        conn.delete("img_%s"%uuid)

        # 3.2 比对（忽略大小写）
        if image_code.lower() != image_code_from_redis.lower():
            return JsonResponse({
                'code': 400,
                'errmsg': '图形验证码输入错误'
            }, status=400)


        # 4、发送短信验证码
        conn = get_redis_connection('sms_code')

        # 判断60秒之内，是否发送过短信——判断标志信息是否存在
        flag = conn.get('flag_%s'%mobile)
        if flag:
            return JsonResponse({'code':400, 'errmsg':'请勿重复发送短信'}, status=400)

        # 构建6位手机验证码
        sms_code = "%06d"%random.randint(0, 999999)
        print("手机验证码：", sms_code)

        # 生成一个redis的pipeline对象
        p = conn.pipeline()
        # 把验证码存入redis
        p.setex(
            "sms_%s"%mobile,
            300,
            sms_code
        )
        # 一旦用户发送了短信,需要在redis中存储一个标志
        p.setex(
            "flag_%s"%mobile,
            60,
            '1'
        )
        p.execute() # 批量执行队列中的指令

        # 发送验证码
        # 同步调用——只有当该发送短信当函数执行完毕，且返回了；代码才会继续往后执行！
        # 如果网络出现了问题，该函数就会一致阻塞在此，导致我们的视图函数无法即使响应！
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)

        # 异步函数调用！
        ccp_send_sms_code.delay(mobile, sms_code)

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })

