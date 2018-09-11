import random

from django.http import HttpResponse
from django.shortcuts import render

import logging
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from meiduo_mall.utils.captcha.captcha import captcha
from meiduo_mall.utils.yuntongxun.sms import CCP
from . import constants
from .serializers import ImageCodeCheckSerializer
from celery_tasks.sms import tasks as sms_tasks

logger = logging.getLogger('django')


class ImageCodeView(APIView):
    """
    图片验证码
    """

    def get(self, request, image_code_id):
        """
        获取图片验证码
        """
        # 生成验证码图片
        text, image = captcha.generate_captcha()
        # 保存验证码内容
        redis_conn = get_redis_connection("verify_codes")
        redis_conn.setex("img_%s" % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)

        # 返回图片
        return HttpResponse(image, content_type="images/jpg")


# url('^sms_codes/(?P<mobile>1[3-9]\d{9})/$', views.SMSCodeView.as_view()),
class SMSCodeView(GenericAPIView):
    """
        短信验证码
        传入参数：
            mobile, image_code_id, text
    """

    def get(self, request, mobile):
        # 校验参数　由序列化器完成
        serializer = ImageCodeCheckSerializer(data=request.query_params)
        # s.get_serializer
        serializer.is_valid(raise_exception=True)

        # 生成短信验证码
        sms_code = "%06d" % random.randint(0, 999999)

        # 保存短信验证码 redis管道
        redis_conn = get_redis_connection('verify_codes')
        pl = redis_conn.pipeline()
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, )
        pl.setex("send_flag_" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        pl.execute()

        # 发送短信
        # try:
        #     ccp = CCP()
        #     expires = constants.SMS_CODE_REDIS_EXPIRES // 60
        #     result = ccp.send_template_sms(mobile, [sms_code, expires], constants.SMS_CODE_TEMP_ID)
        # except Exception as e:
        #     logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
        #     return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # else:
        #     if result == 0:
        #         logger.info("发送验证码短信[正常][ mobile: %s ]" % mobile)
        #     else:
        #         logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 发送短信验证码  用celery
        sms_code_expires = str(constants.SMS_CODE_REDIS_EXPIRES // 60)
        sms_tasks.send_sms_code(mobile, sms_code, sms_code_expires)


    pass
