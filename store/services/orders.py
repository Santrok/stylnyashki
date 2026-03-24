from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models import CartItem, Order, Product


@transaction.atomic
def confirm_order(order_id: int):
    order = Order.objects.select_for_update().get(id=order_id)

    if order.status != Order.Status.NEW:
        raise ValidationError("Подтвердить можно только новый заказ.")

    product_ids = list(order.items.values_list("product_id", flat=True))
    products = Product.objects.select_for_update().filter(id__in=product_ids)

    # если резерв истёк — нельзя подтверждать
    if products.filter(status=Product.Status.RESERVED, reserved_until__lt=timezone.now()).exists():
        raise ValidationError("Резерв истёк. Нужна повторная проверка.")

    # все должны быть RESERVED
    if products.filter(~Q(status=Product.Status.RESERVED)).exists():
        raise ValidationError("Невозможно подтвердить: товары не находятся в резерве.")

    products.update(status=Product.Status.SOLD, reserved_until=None)
    CartItem.objects.filter(product_id__in=product_ids).update(availability=CartItem.Availability.SOLD)

    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def cancel_order(order_id: int):
    order = Order.objects.select_for_update().get(id=order_id)

    if order.status != Order.Status.NEW:
        raise ValidationError("Отменить можно только новый заказ.")

    product_ids = list(order.items.values_list("product_id", flat=True))
    products = Product.objects.select_for_update().filter(id__in=product_ids)

    # возвращаем в продажу то, что было в резерве
    products.filter(status=Product.Status.RESERVED).update(status=Product.Status.AVAILABLE, reserved_until=None)
    CartItem.objects.filter(product_id__in=product_ids).update(availability=CartItem.Availability.AVAILABLE)

    order.status = Order.Status.CANCELED
    order.save(update_fields=["status", "updated_at"])