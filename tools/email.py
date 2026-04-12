from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from ..store.models import Order, Payment


def send_payment_email(order: Order, payment: Payment, status: str):
    ctx = {"order": order, "payment": payment, "site_name": settings.SITE_NAME, "site_url": settings.SITE_URL}
    if status == "paid":
        subject = f"Оплата получена — заказ {order.order_number}"
        text = render_to_string("payments/email/paid.txt", ctx)
        html = render_to_string("payments/email/paid.html", ctx)
    else:
        subject = f"Проблема с оплатой — заказ {order.order_number}"
        text = render_to_string("payments/email/failed.txt", ctx)
        html = render_to_string("payments/email/failed.html", ctx)

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    msg = EmailMultiAlternatives(subject, text, from_email, [order.email])
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)