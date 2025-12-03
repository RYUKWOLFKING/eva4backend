from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator, EmailValidator
from django.utils import timezone


def validate_stock_quantity(value):
    if value < 0:
        raise ValidationError("El stock no puede ser negativo.")


def validate_positive_decimal(value):
    if value < 0:
        raise ValidationError("El valor debe ser positivo.")
    if value == int(value) + 0.5:
        raise ValidationError("Solo se permiten números con 0 o 2 decimales.")


def calculate_dv(rut):
    reversed_rut = rut[::-1]
    total = 0
    factor = 2
    for digit in reversed_rut:
        total += int(digit) * factor
        factor = 2 if factor == 7 else factor + 1
    mod = total % 11
    dv = 11 - mod
    if dv == 11:
        return '0'
    if dv == 10:
        return 'k'
    return str(dv)


def validate_rut(value):
    rut = value.replace('.', '').replace('-', '')
    if len(rut) < 8 or len(rut) > 9:
        raise ValidationError("El RUT debe tener entre 8 y 9 caracteres.")
    if not rut[:-1].isdigit():
        raise ValidationError("El RUT debe contener solo números (excepto el dígito verificador).")
    rut_body = rut[:-1]
    dv = rut[-1]
    calculated_dv = calculate_dv(rut_body)
    if dv.lower() != calculated_dv.lower():
        raise ValidationError(f"Dígito verificador inválido. Debería ser: {calculated_dv}")


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('basico', 'Básico'),
        ('estandar', 'Estándar'),
        ('premium', 'Premium'),
    ]
    company = models.OneToOneField('Company', on_delete=models.CASCADE, related_name='subscription')
    plan_name = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basico')
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company.name} - {self.plan_name}"


class CartItem(models.Model):
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.price


class Cart(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name_plural = "Detalles de Orden"

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.price


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
    ]
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(validators=[EmailValidator()])
    customer_phone = models.CharField(max_length=20, validators=[RegexValidator(r'^\+?56\d{9}$')])
    total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Orden #{self.id} - {self.customer_name}"


class SaleItem(models.Model):
    sale = models.ForeignKey('Sale', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name_plural = "Detalles de Venta"

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.price


class Sale(models.Model):
    PAYMENT_METHODS = [
        ('efectivo', 'Efectivo'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('transferencia', 'Transferencia Bancaria'),
        ('cheque', 'Cheque'),
    ]
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='sales')
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='sales_made')
    total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Venta #{self.id} - {self.branch.name} - ${self.total}"


class Inventory(models.Model):
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='inventory_items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='inventory_items')
    stock = models.IntegerField(default=0, validators=[validate_stock_quantity])
    reorder_point = models.IntegerField(default=10, validators=[validate_stock_quantity], help_text="Cantidad mínima para disparar reorden")
    last_updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['product__name']
        unique_together = ('branch', 'product')
        verbose_name_plural = "Inventarios"

    def __str__(self):
        return f"{self.product.name} - {self.branch.name}: {self.stock} unidades"

    @property
    def needs_reorder(self):
        return self.stock <= self.reorder_point

    @property
    def stock_status(self):
        if self.stock == 0:
            return "Agotado"
        if self.stock <= self.reorder_point:
            return "Stock Bajo"
        return "OK"


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, help_text="Código de producto único")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], help_text="Precio de venta")
    cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], help_text="Costo de adquisición")
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, related_name='products')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def profit_margin(self):
        if self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return 0


class Purchase(models.Model):
    supplier = models.ForeignKey('Supplier', on_delete=models.PROTECT, related_name="purchases")
    branch = models.ForeignKey('Branch', on_delete=models.PROTECT, related_name="purchases")
    product = models.ForeignKey("Product", on_delete=models.PROTECT, related_name="purchases")
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name_plural = "Compras"

    def __str__(self):
        return f"Compra {self.id} - {self.product.sku} x{self.quantity} ({self.supplier.name})"


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rut = models.CharField(max_length=12, unique=True, validators=[validate_rut])
    contact_name = models.CharField(max_length=255)
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(max_length=20, validators=[RegexValidator(r'^\+?56\d{9}$')])
    address = models.TextField(null=True, blank=True)
    payment_terms = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.rut})"


class Branch(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='branches', null=True, blank=True, help_text="Empresa a la que pertenece la sucursal")
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, validators=[RegexValidator(r'^\+?56\d{9}$')])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Sucursales"

    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else 'Sin Empresa'}"


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrador'),
        ('admin_cliente', 'Administrador Cliente'),
        ('gerente', 'Gerente'),
        ('vendedor', 'Vendedor'),
    ]
    rut = models.CharField(max_length=12, unique=True, validators=[validate_rut], help_text="RUT del usuario (ej: 12.345.678-9)")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='vendedor')
    company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True, help_text="Empresa a la que pertenece el usuario")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.role != 'super_admin' and not self.company:
            raise ValidationError("Los usuarios no-admin deben tener una empresa asignada.")


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Nombre de la empresa")
    rut = models.CharField(max_length=12, unique=True, validators=[validate_rut], help_text="RUT de la empresa (ej: 76.123.456-7)")
    address = models.TextField(help_text="Dirección de la empresa", null=True, blank=True)
    phone = models.CharField(max_length=20, validators=[RegexValidator(r'^\+?56\d{9}$')], help_text="Teléfono (ej: +56912345678)")
    email = models.EmailField(validators=[EmailValidator()], help_text="Email de contacto", null=True, blank=True)
    is_provider = models.BooleanField(default=False, help_text="Marca si esta es la empresa proveedora (TemucoSoft)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Empresas"

    def __str__(self):
        return f"{self.name} ({self.rut})"
