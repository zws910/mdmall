import base64

import pickle
from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import GenericAPIView

from goods.models import SKU
from . import constants

# Create your views here.
from django_redis import get_redis_connection
from rest_framework.response import Response

from rest_framework.views import APIView
from .serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectAllSerializer


class CartView(APIView):
    """
    购物车
    """

    def perform_authentication(self, request):
        """
        重写父类的用户验证方法, 不在进入视图前就检查JWT
        :param request:
        :return:
        """

    def post(self, request):
        """
        添加购物车
        :param request:
        :return:
        """
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        # 尝试对请求的用户进行验证
        try:
            user = request.user
        except Exception:
            # 验证失败, 用户未登录
            user = None

        if user is not None and user.is_authenticated:
            # 如果用户已登录, 保存到redis
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            # 用户购物车数据 redis hash
            pl.hincrby('cart_%s' % user.id, sku_id, count)

            # 用户购物车勾选数据 redis set
            if selected:
                pl.sadd('cart_selected_%s' % user.id, sku_id)

            pl.execute()
            return Response(serializer.data)

        else:
            # 如果用户未登录, 保存到cookie

            # 取出cookie中的购物车数据
            cart_str = request.COOKIES.get('cart')
            # 解析
            if cart_str:
                cart_str = cart_str.decode()
                cart_bytes = base64.b64decode(cart_str)
                cart_dict = pickle.loads(cart_bytes)
            else:
                cart_dict = []

            # 如果商品存在购物车中, 累加
            if sku_id in cart_dict:
                cart_dict[sku_id]['count'] += count
                cart_dict[sku_id]['selected'] = selected
            else:
                # 如果商品不在购物车中, 设置
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected,
                }

            cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # 设置cookie
            response = Response(serializer.data)
            response.set_cookie('cart', cart_cookie, max_age=constants.CART_COOKIE_EXPIRES)

    def get(self, request):
        """查询购物车"""
        # 判断用户的登录状态
        try:
            user = request.user
        except Exception:
            user = None

        # 查询
        if user and user.is_authenticated:
            # 如果用户已登录, 从redis中查询 sku_id count selected
            redis_conn = get_redis_connection('cart')
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)

            redis_cart_selected = redis_conn.smembers('cart_selected_%s' % user.id)
            # 遍历redis_cart, 形成cart_dict
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in redis_cart_selected
                }

        else:
            # 如果用户未登录, 从cookie中查询
            cookie_cart = request.COOKIES.get('cart')

            if cookie_cart:
                # 表示cookie中有购物车数据
                # 解析
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                # 表示cookie中没有购物车数据
                cart_dict = {}

        # 查询数据库
        sku_id_list = cart_dict.keys()
        sku_obj_list = SKU.objects.filter(id__in=sku_id_list)

        # 遍历sku_obj_list 向sku对象中添加count和selected属性
        for sku in sku_obj_list:
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']

        # 序列化返回
        serializer = CartSKUSerializer(sku_obj_list, many=True)
        return Response(serializer.data)

    def put(self, request):
        """修改购物车"""
        # sku_id, count, selected
        # 校验
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 判断用户登录状态
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']
        # 如果用户已登录, 修改redis
        try:
            user = request.user
        except Exception:
            user = None

        # 保存
        if user is not None and user.is_authenticated:
            # 如果用户已登录, 修改redis
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # hash
            pl.hset('cart_%s' % user.id, sku_id, count)
            # 处理勾选状态 set
            if selected:
                pl.sadd('cart_selected_%s' % user.id, sku_id)
            else:
                pl.srem('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(serializer.data)

        else:
            # 用户未登录, 在cookie中保存
            cart = request.COOKIES.get('cart')
            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
            else:
                cart = {}

            cart[sku_id] = {
                'count': count,
                'selected': selected,
            }

            cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()

            response = Response(serializer.data)

            # 设置购物车的cookie
            # 需要设置有效期, 否则是临时cookie
            response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)
            return response

    def delete(self, request):
        """删除购物车"""
        # sku_id
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data['sku_id']

        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:
            # 用户已登录, 在redis中保存
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            pl.hdel('cart_%s' % user.id, sku_id)
            pl.srem('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # 用户未登录, 在cookie中保存
            response = Response(status=status.HTTP_204_NO_CONTENT)

            # 使用pickle序列化购物车数据, pickle操作的是bytes类型
            cart = request.COOKIES.get('cart')
            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
                if sku_id in cart:
                    del cart[sku_id]
                    cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()
                    # 设置购物车的cookie
                    # 需要设置有效期, 否则是临时cookie
                    response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)

                return response


class CartSelectAllView(GenericAPIView):
    """
    购物车全选
    """
    serializer_class = CartSelectAllSerializer

    def perform_authentication(self, request):
        pass

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data['selected']

        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:
            # 已登录, redis
            redis_conn = get_redis_connection('cart')
            cart = redis_conn.hgetall('cart_%s' % user.id)
            sku_id_list = cart.keys()

            if selected:
                # 全选
                redis_conn.sadd('cart_selected_%s' % user.id, *sku_id_list)
            else:
                # 取消全选
                redis_conn.srem('cart_selected_%s' % user.id, *sku_id_list)
            return Response({'message': ' OK'})
        else:
            # cookie
            cart = request.COOKIES.get('cart')
            response = Response({'message': 'OK'})

            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
                for sku_id in cart:
                    cart[sku_id]['selected'] = selected
                cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()
                # 设置购物车的cookie
                # 需要设置有效期, 否则是临时cookie
                response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)

            return response
