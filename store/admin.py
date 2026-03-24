"""Admin registrations for store models."""

from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import Product, SizeOption, Cart, CartItem, Category, Order


@admin.register(SizeOption)
class SizeOptionAdmin(admin.ModelAdmin):
    """Admin view for clothing sizes."""

    list_display = ['id', 'value']
    search_fields = ['value']


class CartItemInline(admin.TabularInline):
    """Inline for cart items within Cart admin."""

    model = CartItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin view for managing products.

    Provides list display with key fields, search and filter capabilities.
    """

    list_display = ['name', 'brand', 'category', 'season', 'price', 'discount', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'season', 'brand']
    search_fields = ['name', 'brand', 'category']
    list_editable = ['is_active', 'discount']
    filter_horizontal = ['sizes']
    date_hierarchy = 'created_at'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin view for shopping carts."""

    list_display = ['id', 'user', 'session_key', 'created_at']
    inlines = [CartItemInline]

@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    """
    Класс управления отображения в админ панели сущности: Category
    """
    prepopulated_fields = {"slug": ("title",)}
    mptt_level_indent = 30
    max_level_indent = 3

    def get_queryset(self, request):
        """
        Ограничивает уровень вложенности каждой категории
        """
        qs = super().get_queryset(request)
        return qs.filter(level__lte=self.max_level_indent)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    pass