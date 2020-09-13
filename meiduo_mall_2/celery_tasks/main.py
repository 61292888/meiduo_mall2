from celery import Celery
# 创建对象
celery_app = Celery('meiduo')

# 将config作为配置文件配置给celery
celery_app.config_from_object('celery_tasks.config')

# 让 celery_app 自动捕获目标地址下的任务:
# 就是自动捕获 tasks
celery_app.autodiscover_tasks(['celery_tasks.sms'])