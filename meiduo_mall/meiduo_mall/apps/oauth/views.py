from django.shortcuts import render

# Create your views here.

from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

#  url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
from rest_framework_jwt.settings import api_settings

from oauth.models import OAuthQQUser
from oauth.utils import OAuthQQ
from .exceptions import OAuthQQAPIError
from .serializers import OAuthQQUserSerializer


class QQAuthURLView(APIView):
    """
    获取QQ登录的url
    """

    def get(self, request):
        """
        提供用于qq登录的url
        """
        next = request.query_params.get('next')
        oauth = OAuthQQ(state=next)
        login_url = oauth.get_qq_login_url()
        return Response({'login_url': login_url})


class QQAuthUserView(CreateAPIView):
    """
    QQ登录的用户
    """
    serializer_class = OAuthQQUserSerializer

    def get(self, request):
        """
        获取qq登录的用户数据
        """
        # 获取code
        code = request.query_params.get('code')
        if not code:
            return Response({'message': '缺少code'}, status=status.HTTP_400_BAD_REQUEST)

        oauth = OAuthQQ()

        from oauth.exceptions import OAuthQQAPIError
        try:
            # 凭借code 获取access_token
            access_token = oauth.get_access_token(code)
            # 凭借access_token 获取token_id
            openid = oauth.get_openid(access_token)
        except OAuthQQAPIError:
            return Response({'message': '访问QQ接口异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 根据openid查询数据库OAuthQQUser  判断数据是否存在
        try:
            oauth_qq_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 数据不存在, 处理openid并返回
            access_token = oauth.generate_bind_user_access_token(openid)
            return Response({'access_token': access_token})

        else:
            # 数据存在, 表示用户已经绑定过身份, 签发JWT token
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

            user = oauth_qq_user.user

            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            return Response({
                'username': user.username,
                'user_id': user.id,
                'token': token,
            })

    # def post(self, request):  # 继承createapiview
        # 获取数据

        # 校验数据

        # 判断用户是否存在

        # 如果存在, 绑定, 创建OAuthQQUser数据

        # 如果不存在, 先创建User, 创建OAuthQQUser数据

        # 签发JWT token

