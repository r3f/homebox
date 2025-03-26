from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'locations', views.LocationViewSet, basename='location')
router.register(r'labels', views.LabelViewSet, basename='label')
router.register(r'items', views.ItemViewSet, basename='item')
router.register(r'attachments', views.AttachmentViewSet, basename='attachment')
router.register(r'currencies', views.CurrencyViewSet, basename='currency')
router.register(r'preferences', views.UserPreferenceViewSet, basename='preference')
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')
router.register(r'import-logs', views.ImportLogViewSet, basename='import-log')
router.register(r'collections', views.CollectionViewSet, basename='collection')
router.register(r'maintenance-records', views.MaintenanceRecordViewSet, basename='maintenance-record')
router.register(r'qr-scans', views.QRScanViewSet, basename='qr-scan')

urlpatterns = [
    path('', include(router.urls)),
]