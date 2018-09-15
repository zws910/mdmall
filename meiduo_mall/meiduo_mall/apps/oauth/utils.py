import json
import urllib
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings

from meiduo_mall.utils.exceptions import logger
from oauth import constants
from .exceptions import OAuthQQAPIError
from itsdangerous import TimedJSONWebSignatureSerializer as TJWSSerializer, BadData


class OAuthQQ(object):
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None, state=None):
        self.client_id = client_id or settings.QQ_CLIENT_ID
        self.client_secret = client_secret or settings.QQ_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.QQ_REDIRECT_URI
        self.state = state or settings.QQ_STATE

    def get_qq_login_url(self):
        """
        获取qq登录的网址
        :return: url网址
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'get_user_info',
            'state': self.state
        }
        # urlencode将参数转换为查询字符串
        url = 'https://graph.qq.com/oauth2.0/authorize?' + urlencode(params)
        return url

    def get_access_token(self, code):
        """
        获取acces_token
        :param code: qq提供的code
        :return: access_token
        """
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }

        url = 'https://graph.qq.com/oauth2.0/token?' + urlencode(params)
        # urlopen发送http请求
        try:
            response = urlopen(url)
            # 读取相应体数据, 转换为str类型
            response_data = response.read().decode()  # str

            # 解析access_token
            response_dict = urllib.parse.parse_qs(response_data)
        except Exception as e:
            logger.error('获取access_token异常: %s' % e)
            raise OAuthQQAPIError
        else:
            access_token = response_dict.get('access_token', None)

        return access_token[0]

    def get_openid(self, access_token):
        """获取openid"""
        url = 'https://graph.qq.com/oauth2.0/me?access_token=' + access_token

        try:
            response = urlopen(url)
            # 读取相应体数据, 转换为str类型
            response_data = response.read().decode()  # str

            # 返回的数据 callback( {"client_id":"YOUR_APPID","openid":"YOUR_OPENID"} )\n;

            # 解析
            response_data = response_data[10:-4]
            response_dict = json.loads(response_data)
        except Exception as e:
            logger.error('获取openid异常: %s' % e)
            raise OAuthQQAPIError
        else:
            openid = response_dict.get('openid', None)

        return openid

    def generate_bind_user_access_token(self, openid):
        serializer = TJWSSerializer(secret_key=settings.SECRET_KEY, expires_in=constants.BIND_USER_ACCESS_TOKEN_EXPIRES)
        token = serializer.dumps({'openid': openid})
        return token.decode()

    @staticmethod
    def check_bind_user_access_token(access_token):
        serializer = TJWSSerializer(secret_key=settings.SECRET_KEY, expires_in=constants.BIND_USER_ACCESS_TOKEN_EXPIRES)
        try:
            data = serializer.loads(access_token)
        except BadData:
            return None
        else:
            return data['openid']
