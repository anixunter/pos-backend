"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from core.apps.products.views import CategoryViewSet, SupplierViewSet, ProductViewSet, PurchaseOrderViewSet, InventoryAdjustmentViewSet
from core.apps.billing.views import SalesTransactionViewSet, ProductReturnViewSet
from core.apps.users.views import UserViewSet, CustomerViewSet, CustomerDepositViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='categories')
router.register('suppliers', SupplierViewSet,  basename='suppliers')
router.register('products', ProductViewSet, basename='products')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-orders')
router.register('sales', SalesTransactionViewSet, basename='sales')
router.register('returns', ProductReturnViewSet, basename='returns')
router.register(r'inventory-adjustments', InventoryAdjustmentViewSet, basename='inventory-adjustments')
router.register('users', UserViewSet, basename='users')
router.register('customers', CustomerViewSet, basename='customers')
router.register(r'customers-deposit', CustomerDepositViewSet, basename='customers-deposit')

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
    ),
    path('', include(router.urls)),
]


# Only add debug toolbar in development
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
