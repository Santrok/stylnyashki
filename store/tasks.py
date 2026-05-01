
from __future__ import absolute_import, unicode_literals
import logging
import os
from urllib.parse import urljoin
from uuid import uuid4
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Product, Order
from .utils import convert_uploaded_image_to_avif_content
from tools.telegram_notification import send_telegram_notification

logger = logging.getLogger("store.tasks")

class _FakeRequest:
    """
    Минимальный объект, поддерживающий build_absolute_uri(url)
    Чтобы ваша существующая функция send_telegram_notification могла использовать request.build_absolute_uri(admin_url).
    """
    def __init__(self, absolute_url):
        self._absolute_url = absolute_url

    def build_absolute_uri(self, url=None):
        # игнорируем переданный url и возвращаем готовую абсолютную ссылку,
        # либо, если url задан, корректно конструируем; но обычно мы уже передаём полную ссылку.
        if url:
            # если url абсолютный — вернуть как есть; если относительный — присоединить
            if url.startswith("http://") or url.startswith("https://"):
                return url
            return urljoin(self._absolute_url, url)
        return self._absolute_url


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_telegram_notification_task(self, order_id, include_admin_link=True):
    """
    Celery wrapper: извлекает заказ и вызывает вашу существующую send_telegram_notification.
    Если include_admin_link=True и settings.SITE_URL настроен, формирует admin absolute URL и передаёт
    его через FakeRequest (request.build_absolute_uri(...)) — т.е. ваша оригинальная функция остаётся без изменений.
    """
    try:
        order = Order.objects.get(pk=order_id)
    except ObjectDoesNotExist:
        logger.warning("send_telegram_notification_task: заказ с id=%s не найден", order_id)
        return {"status": "not_found", "order_id": order_id}

    fake_request = None
    if include_admin_link:
        try:
            admin_url = reverse('admin:%s_%s_change' % (order._meta.app_label, order._meta.model_name), args=(order.pk,))
            site_base = getattr(settings, "SITE_URL", "").rstrip("/")
            if site_base:
                admin_abs = urljoin(site_base + "/", admin_url.lstrip("/"))
            else:
                # если SITE_URL не задан — используем относительный путь (в вашей функции будет обработано)
                admin_abs = admin_url
            fake_request = _FakeRequest(admin_abs)
            logger.debug("send_telegram_notification_task: сформирован admin_abs=%s для order=%s", admin_abs, order_id)
        except Exception:
            logger.exception("send_telegram_notification_task: не удалось сформировать admin URL для order=%s", order_id)
            fake_request = None

    try:
        # Вызываем оригинальную функцию — она сама ожидает request или None
        send_telegram_notification(order, request=fake_request)
        logger.info("send_telegram_notification_task: уведомление отправлено для заказа %s", order_id)
        return {"status": "ok", "order_id": order_id}
    except Exception as exc:
        logger.exception("send_telegram_notification_task: ошибка при отправке уведомления для заказа %s: %s", order_id, exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("send_telegram_notification_task: превышено число попыток для заказа %s", order_id)
            return {"status": "failed", "order_id": order_id, "error": str(exc)}


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_product_image(self, temp_storage_path, product_id, filename_base):
    """
    Задача: взять файл temp_storage_path (storage path), конвертировать в AVIF и сохранить в Product.image.
    temp_storage_path — путь в storage (например, 'bulk_tmp/uuid_originalname')
    product_id — id Product в БД
    filename_base — base for resulting filename (без расширения)
    """
    try:
        # Открываем временный файл из default_storage
        with default_storage.open(temp_storage_path, 'rb') as f:
            # convert_uploaded_image_to_avif_content должен принимать file-like и возвращать ContentFile (AVIF)
            avif_content = convert_uploaded_image_to_avif_content(f)

        # Сохраняем в поле Product.image
        p = Product.objects.get(pk=product_id)
        filename = f"{filename_base}.avif"
        p.image.save(filename, avif_content, save=True)
        logger.info("process_product_image: product=%s image saved from temp=%s", product_id, temp_storage_path)

        # Удалим временный файл
        try:
            default_storage.delete(temp_storage_path)
            logger.debug("process_product_image: deleted temp file %s", temp_storage_path)
        except Exception:
            logger.exception("process_product_image: не удалось удалить temp файл %s", temp_storage_path)

        return {"product_id": product_id, "status": "ok"}
    except Exception as exc:
        logger.exception("process_product_image failed for product=%s temp=%s: %s", product_id, temp_storage_path, str(exc))
        try:
            # Optional: mark product as error or attach message
            p = Product.objects.filter(pk=product_id).first()
            if p:
                # тут можно выставить флаг, записать в лог поля и т.п.
                pass
        except Exception:
            logger.exception("process_product_image cleanup failed for product=%s", product_id)
        # Повторная попытка через retry
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("process_product_image: превышено число попыток для product=%s", product_id)
            return {"product_id": product_id, "status": "failed", "error": str(exc)}


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def send_order_confirmation_email_task(self, order_id):
    """
    Отправляет email-подтверждение пользователю о создании заказа.
    Аргументы:
      - order_id: PK заказа
      - public_url: опциональная абсолютная ссылка на публичную страницу заказа (checkout_success)
    Возвращает dict со статусом.
    """
    try:
        order = Order.objects.get(pk=order_id)
    except ObjectDoesNotExist:
        logger.warning("send_order_confirmation_email_task: заказ с id=%s не найден", order_id)
        return {"status": "not_found", "order_id": order_id}

    # Определяем email получателя
    recipient = None
    # Если в заказе явно указан email - используем его, иначе пытаемся взять email пользователя
    if getattr(order, "email", None):
        recipient = order.email.strip()
    elif order.user and getattr(order.user, "email", None):
        recipient = order.user.email.strip()

    if not recipient:
        logger.info("send_order_confirmation_email_task: нет email у заказа %s, пропуск отправки", order_id)
        return {"status": "no_email", "order_id": order_id}

    # Подготовка контекста для шаблонов
    context = {
        "order": order,
        "site_name": getattr(settings, "SITE_NAME", ""),
    }

    try:
        subject = render_to_string("emails/order_confirmation_subject.txt", context).strip()
    except Exception:
        subject = f"Подтверждение заказа #{getattr(order, 'order_number', order.pk)}"

    try:
        text_body = render_to_string("emails/order_confirmation.txt", context)
    except Exception as exc:
        logger.exception("Не удалось отрендерить текст шаблона письма для order %s: %s", order_id, exc)
        text_body = f"Ваш заказ #{getattr(order, 'order_number', order.pk)} успешно создан."

    # Попробуем отрендерить html (необязательно)
    html_body = None
    try:
        html_body = render_to_string("emails/order_confirmation.html", context)
    except Exception:
        html_body = None  # оставим только текст, если HTML-шаблон не доступен

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@localhost"

    try:
        msg = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=[recipient])
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info("Письмо подтверждения заказа отправлено order=%s to=%s", order_id, recipient)
        return {"status": "ok", "order_id": order_id, "to": recipient}
    except Exception as exc:
        logger.exception("Ошибка при отправке письма для order %s: %s", order_id, exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("send_order_confirmation_email_task: превышено число попыток для order=%s", order_id)
            return {"status": "failed", "order_id": order_id, "error": str(exc)}