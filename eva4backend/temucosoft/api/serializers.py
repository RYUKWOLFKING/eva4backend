from rest_framework import serializers
from .models import Product, Inventory, Supplier, CustomUser, Branch, Company, Sale, SaleItem, Order, OrderItem, Subscription, Cart, CartItem, Purchase
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'rut', 'email', 'phone', 'address', 'is_active']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        data.update({
            'username': user.username,
            'email': user.email,
            'role': getattr(user, 'role', None),
            'company_id': user.company.id if getattr(user, 'company', None) else None,
        })

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password_confirm', 'role', 'rut', 'company']

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })

        roles = ['super_admin', 'admin_cliente', 'gerente', 'vendedor']
        role = attrs.get('role')
        if role not in roles:
            raise serializers.ValidationError({'role': 'Rol no válido.'})

        if role == 'super_admin':
            company = attrs.get('company')
            if not company or not getattr(company, 'is_provider', False):
                raise serializers.ValidationError({'company': 'El super_admin sólo puede pertenecer a la empresa proveedora (TemucoSoft).'})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

class CustomUserSerializer(serializers.ModelSerializer):
    company_name = CompanySerializer(source='company', read_only=True)

    def validate_rut(self, value):
        """
        Validar el RUT chileno.
        """
        rut = value.replace('.', '').replace('-', '')
        if len(rut) < 8 or len(rut) > 9:
            raise ValidationError("El RUT debe tener entre 8 y 9 caracteres.")
        
        rut_body = rut[:-1]
        dv = rut[-1]
        calculated_dv = self.calculate_dv(rut_body)

        if dv.lower() != calculated_dv.lower():
            raise ValidationError("El dígito verificador no es válido.")
        
        return value
    
    def calculate_dv(self, rut):
        """
        Calcula el dígito verificador para un RUT chileno.
        """
        reversed_rut = rut[::-1]
        total = 0
        factor = 2
        for digit in reversed_rut:
            total += int(digit) * factor
            factor = 9 if factor == 2 else factor + 1
        mod = total % 11
        return 'k' if mod == 10 else '0' if mod == 11 else str(11 - mod)

    def validate_role(self, value):
        """
        Validar que el rol esté dentro de los roles permitidos.
        """
        roles = ['super_admin', 'admin_cliente', 'gerente', 'vendedor']
        if value not in roles:
            raise serializers.ValidationError("Rol no válido")
        return value

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'rut', 'company_name', 'is_active', 'created_at']


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'price']

class SaleSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = ['branch', 'user', 'items', 'total', 'payment_method', 'created_at']
        extra_kwargs = {'user': {'read_only': True}}

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user:
            validated_data['user'] = user
        sale = Sale.objects.create(**validated_data)

        branch = validated_data['branch']
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            inventory = Inventory.objects.filter(branch=branch, product=product).first()
            if not inventory or inventory.stock < quantity:
                raise serializers.ValidationError({"stock": f"Stock insuficiente para {product.name}"})
            inventory.stock -= quantity
            inventory.save()
            SaleItem.objects.create(sale=sale, **item_data)
        return sale

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['customer_name', 'customer_email', 'items', 'total', 'status', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_sku', 'quantity', 'price', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total']

    def get_total(self, obj):
        return obj.total


class SubscriptionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'company', 'company_name', 'plan_name', 'start_date', 'end_date', 'active', 'created_at']

    def validate(self, attrs):
        start = attrs.get('start_date')
        end = attrs.get('end_date')
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "La fecha de término debe ser mayor que la fecha de inicio."})
        return attrs


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = '__all__'

    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("La fecha de compra no puede ser futura.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            purchase = super().create(validated_data)
            inv, _ = Inventory.objects.get_or_create(
                branch=purchase.branch,
                product=purchase.product,
                defaults={"stock": 0, "reorder_point": 10},
            )
            inv.stock += purchase.quantity
            inv.save()
        return purchase
