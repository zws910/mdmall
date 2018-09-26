from django.conf.urls import url

from . import views


urlpattern = [
    url(r'^/orders/(?P<order_id>\d+)/payment$', views.PaymentView.as_view())
]