from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import (
    FuelTypeViewSet, FuelInventoryViewSet, PumpViewSet, StaffViewSet,
    CustomerViewSet, TransactionViewSet, ReceiptViewSet, NotificationViewSet,
    DailySalesReportViewSet, AuditLogViewSet
)

app_name = 'station_api'

router = DefaultRouter()
router.register(r'fuel-types', FuelTypeViewSet, basename='fueltype')
router.register(r'fuel-inventory', FuelInventoryViewSet, basename='fuelinventory')
router.register(r'pumps', PumpViewSet, basename='pump')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'receipts', ReceiptViewSet, basename='receipt')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'sales-reports', DailySalesReportViewSet, basename='salesreport')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    path('', include(router.urls)),
]
