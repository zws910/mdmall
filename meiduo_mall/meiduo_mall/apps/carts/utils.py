import base64
import pickle

from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, user, response):
    """
    登录时合并购物车, 将cookie中的数据合并到redis中
    1. 商品数量:
    2. 勾选状态:

    """
    # 获取cookie中的购物车数据
    cookie_cart =request.COOKIES.get('cart')

    if not cookie_cart:
        return response


    cookie_cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))

    # 获取redis
    redis_conn = get_redis_connection('cart')
    redis_cart = redis_conn.hgetall('cart_%s' % user.id)

    # 用来存储redis最终保存的商品数量信息的hash数据
    cart = {}
    for sku_id, count in redis_cart.items():
        cart[int(sku_id)] = int(count)

    # 用来记录redis最终操作时, 哪些sku_id是需要勾选新增的
    redis_cart_selected_add = []

    # 用来记录redis最终操作时, 哪些sku_id是需要取消勾选删除的
    redis_cart_selected_remove = []

    # 遍历cookie中的购物车
    for sku_id, count_selected_dict in cookie_cart_dict.items():
        # 处理商品的数量
        cart[sku_id] = count_selected_dict['count']

        # 处理商品的勾选状态
        if count_selected_dict['selected']:
            redis_cart_selected_add.append(sku_id)
        else:
            redis_cart_selected_remove.append(sku_id)

    if cart:
        # 执行redis操作
        pl = redis_conn.pipeline()
        # 设置hash类型
        pl.hmset('cart_%s' % user.id, cart)
        # 设置set类型
        if redis_cart_selected_remove:
            pl.srem('cart_selected_%s' % user.id, *redis_cart_selected_remove)
        if redis_cart_selected_add:
            pl.sadd('cart_selected_%s' % user.id, *redis_cart_selected_add)

        pl.execute()
    # 删除cookie
    response.delete_cookie('cart')
    return response