from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from .models import Product, Inventory, Supplier, Branch, CustomUser, Sale, Order, Company, Subscription, Cart, CartItem, Purchase
from .serializers import (
    ProductSerializer,
    InventorySerializer,
    SupplierSerializer,
    BranchSerializer,
    CustomUserSerializer,
    SaleSerializer,
    OrderSerializer,
    CompanySerializer,
    UserRegistrationSerializer,
    SubscriptionSerializer,
    CartSerializer,
    OrderItemSerializer,
    PurchaseSerializer,
)
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from .permissions import (
    IsSuperAdminTemucoSoft,
    ProductPermission,
    BranchPermission,
    InventoryPermission,
    SupplierPermission,
    UserManagementPermission,
    SalesPermission,
    OrdersPermission,
    PurchasePermission,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class BillingPlansView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdminTemucoSoft]

    def get(self, request):
        total_client_companies = Company.objects.filter(is_provider=False).count()
        total_users = CustomUser.objects.filter(company__is_provider=False).count()
        total_sales = Sale.objects.count()

        data = {
            'total_client_companies': total_client_companies,
            'total_users': total_users,
            'total_sales': total_sales,
            'billing_info': {
                'status': 'active',
                'plan': 'enterprise',
                'currency': 'CLP'
            }
        }
        return Response(data)


class ClientAccountsView(APIView):
    permission_classes = [IsAuthenticated]

    def _allowed(self, request):
        return getattr(request.user, "role", None) in ("super_admin", "admin_cliente")

    def _scope_queryset(self, request):
        if getattr(request.user, "role", None) == "super_admin":
            return CustomUser.objects.filter(company__is_provider=False)
        return CustomUser.objects.filter(company=request.user.company, company__is_provider=False)

    def get(self, request, pk=None):
        if not self._allowed(request):
            return Response({"detail": "No autorizado"}, status=403)
        users = self._scope_queryset(request)
        serializer = CustomUserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request, pk=None):
        if not self._allowed(request):
            return Response({"detail": "No autorizado"}, status=403)
        data = request.data.copy()
        if getattr(request.user, "role", None) == "admin_cliente":
            data["company"] = request.user.company_id
        serializer = UserRegistrationSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(CustomUserSerializer(user).data, status=201)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk=None):
        if not self._allowed(request):
            return Response({"detail": "No autorizado"}, status=403)
        if not pk:
            return Response({"detail": "ID requerido"}, status=400)
        try:
            user = self._scope_queryset(request).get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Usuario no encontrado"}, status=404)

        data = request.data
        for field in ['username', 'email', 'role', 'rut']:
            if field in data:
                setattr(user, field, data[field])
        if 'company' in data and getattr(request.user, "role", None) == "super_admin":
            try:
                comp = Company.objects.get(pk=data['company'], is_provider=False)
            except Company.DoesNotExist:
                return Response({"company": ["Empresa no válida"]}, status=400)
            user.company = comp
        if data.get('password'):
            if data.get('password') != data.get('password_confirm'):
                return Response({"password_confirm": ["Las contraseñas no coinciden"]}, status=400)
            user.set_password(data['password'])
        try:
            user.full_clean()
            user.save()
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(CustomUserSerializer(user).data)

    def delete(self, request, pk=None):
        if not self._allowed(request):
            return Response({"detail": "No autorizado"}, status=403)
        if not pk:
            return Response({"detail": "ID requerido"}, status=400)
        try:
            user = self._scope_queryset(request).get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Usuario no encontrado"}, status=404)
        user.delete()
        return Response(status=204)


class CompanyManagementView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdminTemucoSoft]

    def get(self, request, pk=None):
        companies = Company.objects.filter(is_provider=False)
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data)

    def post(self, request, pk=None):
        serializer = CompanySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(is_provider=False)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk=None):
        if not pk:
            return Response({"detail": "ID requerido"}, status=400)
        try:
            company = Company.objects.get(pk=pk, is_provider=False)
        except Company.DoesNotExist:
            return Response({"detail": "Empresa no encontrada"}, status=404)
        serializer = CompanySerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk=None):
        if not pk:
            return Response({"detail": "ID requerido"}, status=400)
        try:
            company = Company.objects.get(pk=pk, is_provider=False)
        except Company.DoesNotExist:
            return Response({"detail": "Empresa no encontrada"}, status=404)
        company.delete()
        return Response(status=204)


class SalesReportView(APIView):
    permission_classes = [SalesPermission]

    def get(self, request):
        qs = Sale.objects.select_related('branch')
        user = request.user
        if getattr(user, "role", None) != "super_admin":
            qs = qs.filter(branch__company_id=getattr(user, "company_id", None))
        branch = request.GET.get('branch')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if branch:
            qs = qs.filter(branch_id=branch)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        total = qs.aggregate(total=Sum('total'))['total'] or 0
        rows = [
            {
                "branch": s.branch.name,
                "total": s.total,
                "payment_method": s.payment_method,
                "created_at": s.created_at,
            }
            for s in qs.order_by('-created_at')[:100]
        ]
        return Response({"total": total, "rows": rows})


class StockReportView(APIView):
    permission_classes = [InventoryPermission]

    def get(self, request):
        qs = Inventory.objects.select_related('branch', 'product')
        user = request.user
        if getattr(user, "role", None) != "super_admin":
            qs = qs.filter(branch__company_id=getattr(user, "company_id", None))
        data = [
            {
                "branch": inv.branch.name,
                "product": inv.product.name,
                "sku": inv.product.sku,
                "stock": inv.stock,
                "reorder_point": inv.reorder_point,
                "status": inv.stock_status,
            }
            for inv in qs
        ]
        return Response(data)


class CartCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        cart = Cart.objects.filter(user=user).first()
        if not cart or cart.items.count() == 0:
            return Response({"detail": "Carrito vacío"}, status=400)
        total = sum(item.subtotal for item in cart.items.all())
        order = Order.objects.create(
            customer_name=user.username,
            customer_email=user.email,
            customer_phone="+56900000000",
            total=total,
            status="pending",
            shipping_address="",
            notes="Checkout desde carrito",
        )
        from .models import OrderItem as OI
        for item in cart.items.all():
            OI.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.price)
        cart.items.all().delete()
        cart.delete()
        return Response(OrderSerializer(order).data, status=201)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)


class CartAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        product_id = request.data.get('product')
        try:
            quantity = int(request.data.get('quantity', 1))
        except ValueError:
            quantity = 1
        if quantity < 1:
            return Response({"detail": "Cantidad inválida"}, status=400)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"detail": "Producto no encontrado"}, status=404)
        cart, _ = Cart.objects.get_or_create(user=user)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity, "price": product.price},
        )
        if not created:
            item.quantity += quantity
            item.price = product.price
            item.save()
        return Response(CartSerializer(cart).data, status=201)


class SubscriptionMyCompanyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = getattr(request.user, "company", None)
        if not company:
            return Response({"detail": "Sin empresa asociada"}, status=400)
        try:
            sub = Subscription.objects.get(company=company)
        except Subscription.DoesNotExist:
            return Response({"detail": "Sin suscripción"}, status=404)
        return Response(SubscriptionSerializer(sub).data)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'rut': user.rut,
            'company': user.company.name if user.company else None,
            'is_active': user.is_active,
            'created_at': user.created_at
        }
        return Response(data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.select_related("company")
    serializer_class = SubscriptionSerializer
    permission_classes = [IsSuperAdminTemucoSoft]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [OrdersPermission]


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related("branch", "user")
    serializer_class = SaleSerializer
    permission_classes = [SalesPermission]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "super_admin":
            return self.queryset
        return self.queryset.filter(branch__company_id=getattr(user, "company_id", None))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [UserManagementPermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "super_admin":
            return self.queryset
        return self.queryset.filter(company_id=getattr(user, "company_id", None))


class IsSuperAdminOrAdminCliente(BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.role == 'super_admin' or request.user.role == 'admin_cliente')


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [BranchPermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "super_admin":
            return self.queryset
        return self.queryset.filter(company_id=getattr(user, "company_id", None))

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) == "super_admin":
            serializer.save()
        else:
            serializer.save(company=getattr(user, "company", None))

    def perform_update(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) == "super_admin":
            serializer.save()
        else:
            serializer.save(company=getattr(user, "company", None))


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [SupplierPermission]
    pagination_class = StandardResultsSetPagination


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.select_related("branch", "supplier", "product")
    serializer_class = PurchaseSerializer
    permission_classes = [PurchasePermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "super_admin":
            return self.queryset
        return self.queryset.filter(branch__company_id=getattr(user, "company_id", None))

    def perform_create(self, serializer):
        user = self.request.user
        branch = serializer.validated_data.get("branch")
        if getattr(user, "role", None) != "super_admin" and branch and branch.company_id != getattr(user, "company_id", None):
            raise ValidationError({"branch": "No puedes registrar compras en otra empresa."})
        serializer.save()


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.select_related("branch", "product")
    serializer_class = InventorySerializer
    permission_classes = [InventoryPermission]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "super_admin":
            return self.queryset
        return self.queryset.filter(branch__company_id=getattr(user, "company_id", None))


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [ProductPermission]
    pagination_class = StandardResultsSetPagination
