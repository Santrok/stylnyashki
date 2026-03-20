"""Models for the Стильняшки store application."""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class SizeOption(models.Model):
    """Represents an available clothing size (e.g. XS, S, M, L, XL)."""

    value = models.CharField('Размер', max_length=20, unique=True)

    class Meta:
        verbose_name = 'Размер'
        verbose_name_plural = 'Размеры'
        ordering = ['value']

    def __str__(self):
        return self.value


class Product(models.Model):
    """
    Represents a product in the store catalogue.

    Fields:
        name       – product title (название)
        brand      – brand name
        category   – e.g. 'Платья', 'Блузки'
        season     – e.g. 'Лето', 'Зима'
        price      – base price in rubles
        discount   – discount percentage 0-100
        is_active  – visibility flag (активность)
        created_at – auto-set on creation (дата добавления)
        sizes      – M2M link to available SizeOption records
        image      – optional product photo
    """

    name = models.CharField('Название', max_length=255)
    brand = models.CharField('Бренд', max_length=100, blank=True)
    category = models.CharField('Категория', max_length=100, blank=True)
    season = models.CharField('Сезон', max_length=50, blank=True)
    price = models.DecimalField(
        'Цена',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount = models.PositiveSmallIntegerField(
        'Скидка (%)',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)
    sizes = models.ManyToManyField(SizeOption, verbose_name='Размеры', blank=True)
    image = models.ImageField('Изображение', upload_to='products/', blank=True, null=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        """Return price after applying the discount percentage."""
        from decimal import Decimal
        if self.discount:
            factor = Decimal(self.discount) / Decimal(100)
            return round(self.price * (1 - factor), 2)
        return self.price


class Cart(models.Model):
    """Shopping cart tied to a user session or authenticated user."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Пользователь',
    )
    session_key = models.CharField('Ключ сессии', max_length=40, null=True, blank=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f'Корзина {self.user or self.session_key}'

    @property
    def total(self):
        """Return the total cost of all items in the cart."""
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    """A single line in a shopping cart (product + size + quantity)."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name='Корзина')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    size = models.ForeignKey(
        SizeOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Размер',
    )
    quantity = models.PositiveIntegerField('Количество', default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Позиция корзины'
        verbose_name_plural = 'Позиции корзины'
        unique_together = [('cart', 'product', 'size')]

    def __str__(self):
        return f'{self.product.name} × {self.quantity}'

    @property
    def subtotal(self):
        """Return line total using the discounted product price."""
        return self.product.discounted_price * self.quantity
