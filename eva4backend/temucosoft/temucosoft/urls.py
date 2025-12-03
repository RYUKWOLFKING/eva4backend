from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.views.generic import TemplateView
from api.views import (
    UserProfileView,
    ProductViewSet,
    InventoryViewSet,
    SupplierViewSet,
    BranchViewSet,
    CustomUserViewSet,
    SaleViewSet,
    OrderViewSet,
    CompanyManagementView,
    ClientAccountsView,
    BillingPlansView,
    SubscriptionViewSet,
    StockReportView,
    SalesReportView,
    SubscriptionMyCompanyView,
    CartAddView,
    CartView,
    CartCheckoutView,
    PurchaseViewSet,
)
# Crear el router para las vistas de la API
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'sales', SaleViewSet)  
router.register(r'orders', OrderViewSet) 
router.register(r'subscriptions', SubscriptionViewSet)  
router.register(r'purchases', PurchaseViewSet)  
router.register(r'products', ProductViewSet)
router.register(r'inventory', InventoryViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'branches', BranchViewSet)
router.register(r'users', CustomUserViewSet)


urlpatterns = [
   
    path('admin/', admin.site.urls),


    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/subscriptions/me/', SubscriptionMyCompanyView.as_view(), name='subscription-me'),
    path('api/cart/', CartView.as_view(), name='cart-view'),
    path('api/cart/add/', CartAddView.as_view(), name='cart-add'),
    path('api/cart/checkout/', CartCheckoutView.as_view(), name='cart-checkout'),
    path('api/', include(router.urls)), 
    path('api/admin/companies/<int:pk>/', CompanyManagementView.as_view(), name='admin-companies-detail'),
    path('api/admin/accounts/', ClientAccountsView.as_view(), name='admin-client-accounts'),
    path('api/admin/accounts/<int:pk>/', ClientAccountsView.as_view(), name='admin-client-accounts-detail'),
    path('api/admin/billing/', BillingPlansView.as_view(), name='admin-billing'),
    path('api/reports/stock/', StockReportView.as_view(), name='report-stock'),
    path('api/reports/sales/', SalesReportView.as_view(), name='report-sales'),
    path('api/subscriptions/me/', SubscriptionMyCompanyView.as_view(), name='subscription-me'),
    path('', TemplateView.as_view(template_name='inicio.html'), name='index'),  
    path('login/', TemplateView.as_view(template_name='acceso.html'), name='login'),  
    path('dashboard/', TemplateView.as_view(template_name='tablero.html'), name='dashboard'), 
    path('catalog/', TemplateView.as_view(template_name='catalogo.html'), name='catalog'),  
    path('checkout/', TemplateView.as_view(template_name='caja.html'), name='checkout'), 
    path('product_detail/', TemplateView.as_view(template_name='detalle_producto.html'), name='product_detail'),
    path('api/profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/admin/companies/', CompanyManagementView.as_view(), name='admin-companies'),

]

