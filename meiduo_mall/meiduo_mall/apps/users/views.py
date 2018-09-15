from django.shortcuts import render

# Create your views here.

from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users import serializers
from users.models import User


# url(r'^users/$', views.UserView.as_view()),
class UserView(CreateAPIView):
    """
    用户注册
    传入参数: username, password, password2, sms_code, mobile, allow
    """
    serializer_class = serializers.CreateUserSerializer


# url(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
class UsernameCountView(APIView):
    """
    用户名数量
    """

    def get(self, request, username):
        """
        获取指定用户名数量
        """
        count = User.objects.filter(username=username).count()

        data = {
            'username': username,
            'count': count
        }

        return Response(data)


# url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
class MobileCountView(APIView):
    """
    手机号数量
    """

    def get(self, request, mobile):
        """
        获取指定手机号数量
        """
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }

        return Response(data)


# GET /user/
class UserDetailView(RetrieveAPIView):
    """用户基本信息"""
    serializer_class = serializers.UserDetailSerializer
    # 指定访问权限
    permission_classes = [IsAuthenticated]
    # 查询用户数据
    # 重写get_object方法  这里查询集只用查一个
    def get_object(self):
        # 返回当前请求的用户
        # 在类视图对象中, 可以通过类视图对象的属性获取request
        return self.request.user
    # 序列化返回


class EmailView(UpdateAPIView):
    """保存用户邮箱"""
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.EmailSerializer

    def get_object(self, *args, **kwargs):
        return self.request.user