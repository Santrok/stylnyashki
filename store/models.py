"""Models for the Стильняшки store application."""
import secrets
import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from mptt.admin import DraggableMPTTAdmin
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from .utils import convert_image_to_avif

User = get_user_model()


class SizeOption(models.Model):
    value = models.CharField("Размер", max_length=20, unique=True)
    age_label = models.CharField("Возраст (подпись)", max_length=50, blank=True, null=True)
    sort = models.PositiveIntegerField("Сортировка", default=0)

    class Meta:
        verbose_name = "Размер"
        verbose_name_plural = "Размеры"
        ordering = ["sort", "value"]

    def __str__(self):
        if self.age_label:
            return f"{self.value} ({self.age_label})"
        return self.value


class Category(MPTTModel):
    """
    Модель категорий одежды
    связи: дерево связи в самой таблице MPТT(FK)
    """
    title = models.CharField(max_length=255, verbose_name='Категория')
    sub_title = models.CharField(max_length=100, verbose_name="Дополнительный заголовок", blank=True, null=True, help_text="прим. Рост 92–170")
    type = models.CharField(max_length=255,
                            choices=[('level_1', 'Уровень 1'), ('category_2', 'Уровень 2'),
                                     ('category_3', 'Уровень 3'), ('category_4', 'Уровень 4')],
                            verbose_name='Уровень категории')
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                            verbose_name='Отношение к категории одежды')
    icon_class = models.CharField("Класс иконки", max_length=100, blank=True, null=True, help_text="Используется только для главной категории (прим. Мальчики)")
    icon_background_class = models.CharField("Класс фона иконки", max_length=100, blank=True, null=True, help_text="Используется только для главной категории (прим. Мальчики)")
    fav_title = models.CharField(max_length=1000, verbose_name="Заголовок на вкладке", blank=True, null=True)
    main_title = models.CharField(max_length=1000, verbose_name="Главный заголовок", blank=True, null=True)
    keywords = models.CharField(max_length=3000, verbose_name="Ключевые слова", blank=True, null=True)
    keywords_description = models.CharField(max_length=3000, verbose_name="Meta описание", blank=True, null=True)
    slug = models.SlugField(unique=True, verbose_name='URL')

    class Meta:
        verbose_name = 'Kатегория'
        verbose_name_plural = 'Kатегории'

    def __str__(self):
        return self.title


class Product(models.Model):
    """
    Represents a product in the store catalogue.
    """

    class Status(models.TextChoices):
        AVAILABLE = "available", "В продаже"
        RESERVED = "reserved", "В резерве"
        SOLD = "sold", "Продан"

    name = models.CharField('Название', max_length=255)
    brand = models.CharField('Бренд', max_length=100, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, verbose_name="Категория", blank=True, null=True)
    season = models.CharField('Сезон', max_length=50, blank=True, null=True)
    price = models.DecimalField(
        'Цена',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=7
    )
    discount = models.PositiveSmallIntegerField(
        'Скидка (%)',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        blank=True,
        null=True
    )
    is_active = models.BooleanField('Активен', default=True)
    status = models.CharField("Статус", max_length=16, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    reserved_until = models.DateTimeField("Резерв до", null=True, blank=True, db_index=True)
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

    def save(self, *args, **kwargs):

        if self.image and not self.image.url.lower().endswith('avif'):
            convert_image_to_avif(photo=self.image)

        super().save(*args, **kwargs)

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

    class Availability(models.TextChoices):
        AVAILABLE = "available", "Доступно"
        RESERVED = "reserved", "В резерве"
        SOLD = "sold", "Продано"

    availability = models.CharField(
        "Доступность",
        max_length=16,
        choices=Availability.choices,
        default=Availability.AVAILABLE,
        db_index=True,
    )

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


class Favorite(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Пользователь',
    )
    session_key = models.CharField('Ключ сессии', max_length=40, null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'Избранное {self.user or self.session_key}'


class FavoriteItem(models.Model):
    favorite = models.ForeignKey(Favorite, on_delete=models.CASCADE, related_name='items', verbose_name='Избранное')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Позиция избранного'
        verbose_name_plural = 'Позиции избранного'
        unique_together = [('favorite', 'product')]

    def __str__(self):
        return f'{self.product.name}'


class Profile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name="profile")

    middle_name = models.CharField("Отчество", max_length=150, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    city = models.CharField(max_length=64, blank=True, default="")
    instagram_username = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user_id})"


from django.conf import settings
from django.db import models


class Address(models.Model):
    class Type(models.TextChoices):
        POST = "post", "Почта"
        EUROPOST = "europost", "Европочта"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    type = models.CharField(max_length=16, choices=Type.choices)

    # ФИО
    last_name = models.CharField("Фамилия", max_length=150, blank=True, default="")
    first_name = models.CharField("Имя", max_length=150, blank=True, default="")
    middle_name = models.CharField("Отчество", max_length=150, blank=True, default="")

    phone = models.CharField("Телефон", max_length=32, blank=True, default="")

    # --- Почта ---
    postal_index = models.CharField("Почтовый индекс", max_length=16, blank=True, default="")
    city = models.CharField("Город", max_length=64, blank=True, default="")
    street = models.CharField("Улица", max_length=128, blank=True, default="")
    house = models.CharField("Дом", max_length=32, blank=True, default="")
    apartment = models.CharField("Квартира", max_length=32, blank=True, default="")  # optional

    # --- Европочта ---
    europost_branch_number = models.CharField("Номер отделения Европочты", max_length=32, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # один адрес каждого типа на пользователя => редактирование = update этой записи
            models.UniqueConstraint(fields=["user", "type"], name="uniq_address_per_user_per_type"),
        ]

    def __str__(self):
        return f"Address(user={self.user_id}, type={self.type})"


from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        CONFIRMED = "confirmed", "Подтверждён"
        CANCELED = "canceled", "Отменён"

    class DeliveryType(models.TextChoices):
        POST = "post", "Почта"
        EUROPOST = "europost", "Европочта"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "При получении (наложенный платеж)"
        ERIP = "erip", "АИС \"Расчёт\" (ЕРИП)"
        CARD = "card", "Онлайн картой"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Ожидается"
        PAID = "paid", "Оплачен"
        FAILED = "failed", "Неудача"
        REFUNDED = "refunded", "Возврат"

    payment_method = models.CharField(
        "Способ оплаты",
        max_length=16,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
    )

    payment_status = models.CharField(
        "Статус оплаты",
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    # идентификатор платежа шлюза (при наличии)
    payment_id = models.CharField("ИД платежа (шлюз)", max_length=128, blank=True, default="", db_index=True)
    paid_at = models.DateTimeField("Дата оплаты", null=True, blank=True)

    retry_token = models.UUIDField("Токен повторной оплаты", default=uuid.uuid4, editable=False, db_index=True)

    order_number = models.CharField(
        "Номер заказа",
        max_length=32,
        unique=True,
        editable=False,
        db_index=True,
        blank=True,
        default="",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Пользователь",
    )

    status = models.CharField(
        "Статус заказа",
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
    )
    public_id = models.UUIDField("Публичный идентификатор", default=uuid.uuid4, unique=True, editable=False)

    delivery_type = models.CharField(
        "Тип доставки",
        max_length=16,
        choices=DeliveryType.choices,
    )

    last_name = models.CharField("Фамилия", max_length=150)
    first_name = models.CharField("Имя", max_length=150)
    middle_name = models.CharField("Отчество", max_length=150)
    phone = models.CharField("Телефон", max_length=32)
    instagram = models.CharField(
        "Instagram",
        max_length=64,
        blank=False,
        default="",
        help_text="Ник в Instagram для связи (например: username или @username).",
    )
    email = models.EmailField("Email")

    # --- Доставка: Почта ---
    postal_index = models.CharField("Почтовый индекс", max_length=16, blank=True, default="")
    city = models.CharField("Город", max_length=64, blank=True, default="")
    street = models.CharField("Улица", max_length=128, blank=True, default="")
    house = models.CharField("Дом", max_length=32, blank=True, default="")
    apartment = models.CharField("Квартира", max_length=32, blank=True, default="")

    # --- Доставка: Европочта ---
    europost_branch_number = models.CharField("Номер отделения Европочты", max_length=32, blank=True, default="")

    comment = models.TextField("Комментарий к заказу", blank=True, default="")

    subtotal = models.DecimalField(
        "Сумма товаров",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    delivery_price = models.DecimalField(
        "Стоимость доставки",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        "Итого",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ #{self.order_number}"

    def recalc_totals(self, save: bool = True):
        subtotal = Decimal("0.00")
        for item in self.items.all():
            subtotal += (item.price * item.quantity)

        self.subtotal = subtotal
        self.total = (self.subtotal or Decimal("0.00")) + (self.delivery_price or Decimal("0.00"))

        if save:
            self.save(update_fields=["subtotal", "total", "updated_at"])

    def _generate_order_number(self) -> str:
        # SN-YYMMDD-XXXXXX (буквы+цифры без неоднозначных символов)
        alphabet = "23456789" + "ABCDEFGHJKMNPQRSTUVWXYZ"  # без 0,O,I,1
        rnd = "".join(secrets.choice(alphabet) for _ in range(6))
        return f"SN-{self.created_at:%y%m%d}-{rnd}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)

        # генерируем номер после первого save, чтобы уже был created_at
        if creating and not self.order_number:
            # пробуем несколько раз на случай коллизии
            for _ in range(10):
                candidate = self._generate_order_number()
                if not Order.objects.filter(order_number=candidate).exists():
                    self.order_number = candidate
                    super().save(update_fields=["order_number"])
                    break


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ",
    )

    product = models.ForeignKey(
        "store.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="Товар",
    )

    size = models.ForeignKey(
        "store.SizeOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Размер",
    )

    product_name = models.CharField("Название товара", max_length=255)
    price = models.DecimalField("Цена за единицу", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField("Количество", default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def line_total(self):
        return (self.price or Decimal("0.00")) * self.quantity


class Payment(models.Model):
    """
    Модель для учета платёжных транзакций, связанных с заказами.
    Хранит данные по каждой попытке / сессии оплаты через шлюз.
    """
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидается"
        PAID = "paid", "Оплачен"
        FAILED = "failed", "Неудача"
        REFUNDED = "refunded", "Возврат"

    order = models.ForeignKey(Order, related_name="payments", on_delete=models.CASCADE, verbose_name="Заказ")
    gateway = models.CharField("Платёжный шлюз", max_length=64, default="webpay")  # 'webpay' пока
    gateway_payment_id = models.CharField("ИД в шлюзе", max_length=128, blank=True, default="", db_index=True)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField("Валюта", max_length=8, default="BYN")
    status = models.CharField("Статус", max_length=16, choices=Status.choices, default=Status.PENDING)
    payload = models.JSONField("Данные платежа (raw)", null=True, blank=True)  # raw request/response для аудита
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    paid_at = models.DateTimeField("Дата оплаты", null=True, blank=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.pk} ({self.gateway}) order={self.order_id} amount={self.amount} {self.currency}"

    def mark_paid(self, payload: dict | None = None):
        """
        Отметить платёж как оплаченный: обновляем запись Payment и агрегируем состояние в Order.
        payload — опционально: сырые данные от шлюза (webhook).
        """
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        if payload is not None:
            self.payload = payload
        self.save(update_fields=["status", "paid_at", "payload", "updated_at"])

        # Обновляем статус заказа (агрегированно)
        order = self.order
        order.payment_status = Order.PaymentStatus.PAID
        order.payment_id = self.gateway_payment_id or order.payment_id
        order.paid_at = self.paid_at
        # Переводим заказ в CONFIRMED (или другую логику — обсуждается)
        order.status = Order.Status.CONFIRMED
        order.save(update_fields=["payment_status", "payment_id", "paid_at", "status"])

    def mark_failed(self, payload: dict | None = None):
        """Отметить платёж как неудачный."""
        self.status = self.Status.FAILED
        if payload is not None:
            self.payload = payload
        self.save(update_fields=["status", "payload", "updated_at"])

    def mark_refunded(self, payload: dict | None = None):
        """Отметить платёж как возвращённый/возврат."""
        self.status = self.Status.REFUNDED
        if payload is not None:
            self.payload = payload
        self.save(update_fields=["status", "payload", "updated_at"])
        # при возврате — обновите order.payment_status по вашей политике
        order = self.order
        order.payment_status = Order.PaymentStatus.REFUNDED
        order.save(update_fields=["payment_status"])


class CompanyInfo(models.Model):
    name = models.CharField("Наименование", max_length=250, default='ООО «Стиль-Няшки»')
    director = models.CharField("Руководитель", max_length=250, blank=True, default='Макодай А.П.')

    legal_address = models.CharField("Юридический адрес", max_length=512, blank=True, null=True)
    inn = models.CharField("УНП / ИНН", max_length=64, blank=True, null=True)

    bank_account = models.CharField("Расчетный счет (Р/с)", max_length=128, blank=True, null=True)
    bank_name = models.CharField("Банк (наименование)", max_length=255, blank=True, null=True)
    bank_address = models.CharField("Адрес банка", max_length=255, blank=True, null=True)
    bic = models.CharField("БИК / SWIFT", max_length=64, blank=True, null=True)

    phone = models.CharField("Телефон", max_length=64, blank=True, null=True)
    email = models.EmailField("Электронная почта", blank=True, null=True)

    registration_note = models.TextField("Сведения о регистрации / режим работы", blank=True, null=True)

    # optional: ordering or timestamps
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Информация о компании"
        verbose_name_plural = "Информация о компании"

    def __str__(self):
        return self.name


class SiteConfiguration(models.Model):
    payment_cod = models.BooleanField("Наложенный платеж (COD)", default=True)
    payment_erip = models.BooleanField("АИС «Расчёт» (ЕРИП)", default=False)
    payment_card = models.BooleanField("Онлайн картой (Webpay)", default=False)

    class Meta:
        verbose_name = "Конфигурация сайта"
        verbose_name_plural = "Конфигурация сайта"

    def __str__(self):
        return "Конфигурация сайта"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1, defaults={})
        return obj