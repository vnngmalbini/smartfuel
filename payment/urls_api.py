from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import (
    PaymentProviderViewSet, PaymentTransactionViewSet,
    PaymentGatewayLogViewSet, CardTokenViewSet
)

app_name = 'payment_api'

router = DefaultRouter()
router.register(r'providers', PaymentProviderViewSet, basename='paymentprovider')
router.register(r'transactions', PaymentTransactionViewSet, basename='paymenttransaction')
router.register(r'gateway-logs', PaymentGatewayLogViewSet, basename='paymentgatewaylog')
router.register(r'card-tokens', CardTokenViewSet, basename='cardtoken')

urlpatterns = [
    path('', include(router.urls)),
]
