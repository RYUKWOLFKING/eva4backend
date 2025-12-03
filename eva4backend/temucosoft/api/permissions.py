from rest_framework.permissions import BasePermission


class IsSuperAdminTemucoSoft(BasePermission):
	"""Permite acceso solo a usuarios con rol `super_admin` que pertenezcan
	a la empresa proveedora (is_provider=True), es decir TemucoSoft.
	"""
	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		if not user or not user.is_authenticated:
			return False
		if getattr(user, 'role', None) != 'super_admin':
			return False

		company = getattr(user, 'company', None)
		if company is None:
			return True
		return bool(getattr(company, 'is_provider', False))


class ProductPermission(BasePermission):
	"""Permite lectura pública; escritura solo a super_admin/admin_cliente/gerente."""
	safe_roles = ('super_admin', 'admin_cliente', 'gerente')

	def has_permission(self, request, view):
		if request.method in ('GET', 'HEAD', 'OPTIONS'):
			return True
		user = getattr(request, 'user', None)
		return bool(user and user.is_authenticated and getattr(user, 'role', None) in self.safe_roles)

	def has_object_permission(self, request, view, obj):
		if request.method in ('GET', 'HEAD', 'OPTIONS'):
			return True
		return self.has_permission(request, view)


class BranchPermission(BasePermission):
	"""Acceso a sucursales para super_admin o admin_cliente."""
	allowed_roles = ('super_admin', 'admin_cliente')
	read_roles = ('super_admin', 'admin_cliente', 'gerente', 'vendedor')

	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		if request.method in ('GET', 'HEAD', 'OPTIONS'):
			return bool(user and user.is_authenticated and getattr(user, 'role', None) in self.read_roles)
		return bool(user and user.is_authenticated and getattr(user, 'role', None) in self.allowed_roles)


class InventoryPermission(BasePermission):
	"""Inventario:
	- GET/HEAD/OPTIONS: super_admin, admin_cliente, gerente, vendedor
	- POST/PUT/PATCH/DELETE: solo super_admin, admin_cliente, gerente
	"""
	read_roles = ('super_admin', 'admin_cliente', 'gerente', 'vendedor')
	write_roles = ('super_admin', 'admin_cliente', 'gerente')

	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		role = getattr(user, 'role', None)
		if request.method in ('GET', 'HEAD', 'OPTIONS'):
			return bool(user and user.is_authenticated and role in self.read_roles)
		return bool(user and user.is_authenticated and role in self.write_roles)


class PurchasePermission(BasePermission):
	"""Compras: super_admin, admin_cliente, gerente."""
	allowed_roles = ('super_admin', 'admin_cliente', 'gerente')

	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		return bool(user and user.is_authenticated and getattr(user, 'role', None) in self.allowed_roles)


class SupplierPermission(BasePermission):
	"""Proveedores: admin_cliente, gerente o super_admin."""
	allowed_roles = ('super_admin', 'admin_cliente', 'gerente')

	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		return bool(user and user.is_authenticated and getattr(user, 'role', None) in self.allowed_roles)


class UserManagementPermission(BasePermission):
	"""Usuarios: solo super_admin y admin_cliente. Admin_cliente solo dentro de su empresa (se filtra en queryset)."""
	allowed_roles = ('super_admin', 'admin_cliente')

	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		return bool(user and user.is_authenticated and getattr(user, 'role', None) in self.allowed_roles)

	def has_object_permission(self, request, view, obj):
		user = getattr(request, 'user', None)
		if not user or not user.is_authenticated:
			return False
		if getattr(user, 'role', None) == 'super_admin':
			return True

		return getattr(obj, 'company_id', None) == getattr(user, 'company_id', None)


class SalesPermission(BasePermission):
	"""Ventas POS: vendedores, gerentes, admin_cliente y super_admin."""
	allowed_roles = ('super_admin', 'admin_cliente', 'gerente', 'vendedor')

	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		return bool(user and user.is_authenticated and getattr(user, 'role', None) in self.allowed_roles)


class OrdersPermission(BasePermission):
	"""Órdenes ecommerce:
	- GET/HEAD/OPTIONS: super_admin, admin_cliente, gerente, vendedor (para ver ventas del carrito)
	- Escritura: super_admin, admin_cliente, gerente
	"""
	read_roles = ('super_admin', 'admin_cliente', 'gerente', 'vendedor')
	write_roles = ('super_admin', 'admin_cliente', 'gerente')

	def has_permission(self, request, view):
		user = getattr(request, 'user', None)
		role = getattr(user, 'role', None)
		if request.method in ('GET', 'HEAD', 'OPTIONS'):
			return bool(user and user.is_authenticated and role in self.read_roles)
		return bool(user and user.is_authenticated and role in self.write_roles)

