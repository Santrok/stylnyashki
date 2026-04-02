"""Admin registrations for store models."""
import csv

from django.contrib import admin
from django.db.models import ExpressionWrapper, F, Value, DecimalField
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from mptt.admin import DraggableMPTTAdmin, TreeRelatedFieldListFilter
from django.utils.translation import gettext_lazy as _

from .models import Product, SizeOption, Cart, CartItem, Category, Order, CompanyInfo, OrderItem


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


class CategoryTreeRelatedFieldListFilter(TreeRelatedFieldListFilter):
    title = 'Категория'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin view for managing products with improved usability:
    - thumbnail preview
    - discounted price column
    - useful filters and actions
    - CSV export
    """

    @admin.display(description='')
    def get_html_photo(self, object):
        return mark_safe(f"<img src='{object.image.url}' style='width=80px; height: 80px;'>")

    # --- display ---
    @admin.display(description='Фото')
    def thumbnail(self, obj):
        if obj.image:
            url = obj.image.url
            # ссылка на форму редактирования продукта в админке
            change_url = reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=(obj.pk,))
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="width:200px;height:200px;object-fit:cover;border-radius:6px;" /></a>',
                change_url, url
            )
        return '-'

    @admin.display(ordering='price', description='Цена (со скидкой)')
    def discounted_price_display(self, obj):
        # если аннотация присутствует, используем её; иначе используем метод модели
        dp = getattr(obj, 'discounted_price_ann', None)
        if dp is None:
            try:
                dp = obj.discounted_price
            except Exception:
                dp = obj.price
        return dp

    list_display = [
        'name',
        'thumbnail',
        'category',
        'brand',
        'price',
        'discount',
        'discounted_price_display',
        'is_active',
        'status',
        'created_at',
    ]

    # --- filters/search ---
    list_filter = [
        'is_active',
        ('category', CategoryTreeRelatedFieldListFilter) if CategoryTreeRelatedFieldListFilter else 'category',
        'brand',
        'season',
        'status',
    ]
    search_fields = ['name', 'brand', 'category__name']
    list_editable = ['is_active', 'discount']
    filter_horizontal = ['sizes']
    date_hierarchy = 'created_at'
    list_select_related = ('category',)
    list_per_page = 50

    # readonly (computed) fields in change form
    readonly_fields = ('created_at', 'discounted_price_display', 'thumbnail')

    # organize fields in change form
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'brand', 'category', 'season', ('image', 'thumbnail'), 'is_active', 'status', 'reserved_until')
        }),
        ('Цены', {
            'fields': ('price', 'discount', 'discounted_price_display'),
        }),
        ('Наличие / размеры', {
            'fields': ('sizes',),
        }),
        ('Метаданные', {
            'fields': ('created_at',),
        }),
    )

    actions = [
        'make_available',
        'make_reserved',
        'make_sold',
        'set_active',
        'set_inactive',
        'export_as_csv',
    ]

    # --- queryset optimization + annotate discounted price ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # аннотируем рассчитанную цену со скидкой, чтобы показать/сортировать
        # discounted = price * (1 - discount/100)
        discounted_expr = ExpressionWrapper(
            F('price') * (Value(1) - (F('discount') / Value(100))),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
        qs = qs.select_related('category').prefetch_related('sizes').annotate(discounted_price_ann=discounted_expr)
        return qs

    # --- actions implementations ---
    def make_available(self, request, queryset):
        updated = queryset.update(status=Product.Status.AVAILABLE)
        self.message_user(request, f'Помечено как "В продаже": {updated} товар(ов).')
    make_available.short_description = 'Пометить как "В продаже"'

    def make_reserved(self, request, queryset):
        updated = queryset.update(status=Product.Status.RESERVED)
        self.message_user(request, f'Помечено как "В резерве": {updated} товар(ов).')
    make_reserved.short_description = 'Пометить как "В резерве"'

    def make_sold(self, request, queryset):
        updated = queryset.update(status=Product.Status.SOLD, is_active=False)
        self.message_user(request, f'Помечено как "Продан": {updated} товар(ов). (Выключены из выдачи)')
    make_sold.short_description = 'Пометить как "Продан" и отключить'

    def set_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Включено в публикацию: {updated} товар(ов).')
    set_active.short_description = 'Включить (is_active=True)'

    def set_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Отключено из публикации: {updated} товар(ов).')
    set_inactive.short_description = 'Отключить (is_active=False)'

    def export_as_csv(self, request, queryset):
        """
        Экспорт выбранных товаров в CSV: id, name, brand, category, price, discount, final_price, is_active, status
        """
        meta = self.model._meta
        filename = f"{meta.model_name}_export.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        header = ['id', 'name', 'brand', 'category', 'price', 'discount', 'final_price', 'is_active', 'status', 'created_at']
        writer.writerow(header)
        for obj in queryset.select_related('category'):
            final_price = getattr(obj, 'discounted_price_ann', None)
            if final_price is None:
                final_price = obj.discounted_price
            writer.writerow([
                obj.pk,
                obj.name,
                obj.brand or '',
                obj.category.name if obj.category else '',
                str(obj.price),
                str(obj.discount or 0),
                str(final_price),
                'yes' if obj.is_active else 'no',
                obj.get_status_display(),
                obj.created_at.isoformat(),
            ])
        return response
    export_as_csv.short_description = 'Экспортировать как CSV'

    # --- optional: nicer display for price fields ---
    @admin.display(ordering='price', description='Цена')
    def price_display(self, obj):
        return obj.price


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


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        # Allow add only if there is no instance yet
        if CompanyInfo.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion via admin to keep at least one set of details
        return False


class OrderItemInline(admin.TabularInline):

    @admin.display(description='')
    def get_html_photo(self, object):
        return mark_safe(f"<img src='{object.product.image.url}' style='width=150px; height: 150px;'>")

    model = OrderItem
    fk_name = 'order'
    extra = 0
    readonly_fields = ('product', 'product_name', 'size', 'price', 'get_html_photo', 'line_total')
    fields = ('product', 'get_html_photo', 'product_name', 'size', 'price', 'line_total')
    can_delete = False
    show_change_link = False



    def has_add_permission(self, request, obj):
        # обычно позиции создаются из публичной части/логики магазина, не из админки
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'public_id',
        'user_display',
        'total',
        'status_badge',
        'delivery_type',
        'created_at',
    )
    list_filter = ('status', 'delivery_type', 'created_at')
    search_fields = ('order_number', 'public_id', 'user__email', 'first_name', 'last_name', 'phone')
    readonly_fields = ('order_number', 'public_id', 'created_at', 'updated_at', 'subtotal', 'total')
    ordering = ('-created_at',)
    inlines = [OrderItemInline]
    actions = ['make_confirmed', 'make_canceled']
    list_select_related = ('user',)

    fieldsets = (
        ('Основное', {
            'fields': ('order_number', 'public_id', 'user', 'status', 'delivery_type')
        }),
        ('Получатель', {
            'fields': ('last_name', 'first_name', 'middle_name', 'phone', 'instagram')
        }),
        ('Адрес доставки (Почта)', {
            'fields': ('postal_index', 'city', 'street', 'house', 'apartment'),
        }),
        ('Адрес доставки (Европочта)', {
            'fields': ('europost_branch_number',),
        }),
        ('Суммы', {
            'fields': ('subtotal', 'delivery_price', 'total'),
        }),
        ('Прочее', {
            'fields': ('comment',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return f"{obj.first_name} {obj.last_name}" if (obj.first_name or obj.last_name) else '—'
    user_display.short_description = 'Покупатель'

    def status_badge(self, obj):
        """
        Отображение статуса с цветом.
        """
        color_map = {
            Order.Status.NEW: '#f3f4f6',         # серый фон
            Order.Status.CONFIRMED: '#ECFDF5',   # зелёный фон
            Order.Status.CANCELED: '#FFF1F2',    # красный фон
        }
        text_color_map = {
            Order.Status.NEW: '#6b7280',
            Order.Status.CONFIRMED: '#065F46',
            Order.Status.CANCELED: '#991B1B',
        }
        bg = color_map.get(obj.status, '#f3f4f6')
        color = text_color_map.get(obj.status, '#111827')
        label = obj.get_status_display()
        return format_html(
            '<span style="display:inline-block;padding:4px 10px;border-radius:10px;background:{};color:{};font-weight:800;">{}</span>',
            bg, color, label
        )
    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'

    # Admin actions
    def make_confirmed(self, request, queryset):
        updated = queryset.update(status=Order.Status.CONFIRMED)
        self.message_user(request, f'Отмечено как "Подтверждён" {updated} заказ(ов).')
    make_confirmed.short_description = 'Пометить как Подтверждён'

    def make_canceled(self, request, queryset):
        updated = queryset.update(status=Order.Status.CANCELED)
        self.message_user(request, f'Отмечено как "Отменён" {updated} заказ(ов).')
    make_canceled.short_description = 'Пометить как Отменён'

    # оптимизация queryset
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

    # опция — в списке кликаем по номеру заказа, попадаем в change form
    # можно добавить ссылку на публичную страницу заказа по public_id
    def public_order_link(self, obj):
        url = reverse('account_order_detail', args=[obj.public_id])
        return format_html('<a href="{}" target="_blank">Открыть (публично)</a>', url)
    public_order_link.short_description = 'Публичная страница'