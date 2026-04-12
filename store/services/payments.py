import hmac
import hashlib
from django.conf import settings

def sign_webpay_payload(params: dict) -> str:
    """
    Простая HMAC-SHA256 подпись по отсортированным параметрам.
    ВНИМАНИЕ: это пример. Точную схему подписи и набор полей возьмите из документации Webpay.
    """
    secret = settings.WEBPAY["SECRET_KEY"].encode("utf-8")
    # Создаём каноническую строку: ключи в алфавитном порядке, key=value разделённые &
    items = [(k, str(params[k])) for k in sorted(params.keys())]
    payload = "&".join(f"{k}={v}" for k, v in items)
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return sig

def build_webpay_form_data(payment):
    """
    Сформировать набор полей для отправки на Webpay (пример).
    payment — экземпляр модели Payment (с полями amount, currency и т.д.)
    Возвращает dict полей, которые нужно положить в скрытые input и отправить на PAYMENT_URL.
    Замените структуру полей согласно спецификации Webpay.
    """
    order = payment.order
    params = {
        "merchant_id": settings.WEBPAY["MERCHANT_ID"],
        "order_id": str(order.public_id),            # public id заказа
        "amount": f"{payment.amount:.2f}",
        "currency": payment.currency or settings.WEBPAY.get("CURRENCY", "BYN"),
        "description": f"Order {order.order_number}",
        "return_url": settings.WEBPAY["RETURN_URL"],
        "callback_url": settings.WEBPAY["CALLBACK_URL"],
    }
    # подпись (пример)
    params["signature"] = sign_webpay_payload(params)
    return params