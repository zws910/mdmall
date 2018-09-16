from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from oauth.models import OAuthQQUser
from users.models import User
from .utils import OAuthQQ


class OAuthQQUserSerializer(serializers.ModelSerializer):
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    access_token = serializers.CharField(label='操作凭证', write_only=True)
    token = serializers.CharField(read_only=True)
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$')

    class Meta:
        model = User
        fields = ('mobile', 'password', 'sms_code', 'access_token', 'id', 'username', 'token')
        extra_kwargs = {
            'username': {
                'read_only': True
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    # 校验数据
    def validate(self, attrs):
        # 校验access_token
        access_token = attrs['access_token']

        openid = OAuthQQ.check_bind_user_access_token(access_token)
        if not openid:
            raise serializers.ValidationError('无效的access_token')

        attrs['openid'] = openid

        # 校验短信验证码
        mobile = attrs['mobile']
        sms_code = attrs['sms_code']
        redis_conn = get_redis_connection('verify_codes')
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        if real_sms_code.decode() != sms_code:
            raise serializers.ValidationError('短信验证码错误')

        # 如果用户存在, 检查用户密码
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            pass
        else:
            password = attrs['password']
            if not user.check_password(password):
                raise serializers.ValidationError('密码错误')

            attrs['user'] = user
        return attrs

    def create(self, validated_data):
        """保存"""
        openid = validated_data['openid']
        user = validated_data.get('user')
        mobile = validated_data['mobile']
        password = validated_data['password']

        print(openid, user)
        if user:
            # 若果存在, 绑定身份 创建数据
            print(user, openid)  # for test
            OAuthQQUser.objects.create(user=user, openid=openid)
        else:
            # 如果不存在, 先创建user, 创建oauthqquser数据
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)

        # 签发 JWT token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        user.token = token

        return user
