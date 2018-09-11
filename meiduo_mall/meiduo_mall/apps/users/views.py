from django.shortcuts import render

# Create your views here.
from rest_framework.generics import CreateAPIView

from users.serializers import CreateUserSerializer


# url(r'^users/$', views.UserView.as_view()),
class UserView(CreateAPIView):
    """
    用户注册
    传入参数: username, password, password2, sms_code, mobile, allow
    """
    serializer_class = CreateUserSerializer



    # 接收参数

    # 校验参数

    # 保存用户数据


    # 序列化 返回
