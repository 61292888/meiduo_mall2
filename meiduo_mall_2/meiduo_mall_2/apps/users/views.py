from django.http import JsonResponse
from django.views import View
from users.models import User

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