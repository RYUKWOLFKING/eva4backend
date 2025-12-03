from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, InventoryViewSet, SupplierViewSet, BranchViewSet, CustomUserViewSet, SaleViewSet, OrderViewSet
from .views import CompanyManagementView, ClientAccountsView, BillingPlansView

# Crear un enrutador para las vistas de la API
router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'inventory', InventoryViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'branches', BranchViewSet)
router.register(r'users', CustomUserViewSet)
router.register(r'sales', SaleViewSet)  # Endpoints de Ventas
router.register(r'orders', OrderViewSet)  # Endpoints de Órdenes

urlpatterns = [
    # Endpoints admin (protegidos por permiso IsSuperAdminTemucoSoft en las vistas)
    path('api/admin/companies/', CompanyManagementView.as_view(), name='company_management'),
    path('api/admin/client-accounts/', ClientAccountsView.as_view(), name='client_accounts'),
    path('api/admin/billing/', BillingPlansView.as_view(), name='billing_plans'),

    # Endpoints estándar registrados en el router
    path('', include(router.urls)),  # Aquí se incluyen todos los endpoints de la API registrados en el router
]
