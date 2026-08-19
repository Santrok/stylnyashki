import json
import logging
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.urls import reverse
from django.utils.html import escape

logger = logging.getLogger(__name__)


def send_telegram_notification(order, request=None):
    """
    Отправляет текст уведомления о новом заказе в Telegram через Bot API.
    Если request передан — пытается сформировать ссылку на публичную страницу заказа.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_NEW_ORDER_CHAT_ID", "")

    if not token or not chat_id:
        # настройки не заданы — ничего не делаем
        logger.debug("Telegram settings not configured; skipping notification.")
        return

    # Собираем краткую информацию по заказу
    try:
        lines = []
        # заголовок
        lines.append(f"<b>Новый заказ #{order.order_number}</b>")
        # ссылка на публичную страницу (если есть request)
        if request:
            try:
                admin_url = reverse('admin:%s_%s_change' % (order._meta.app_label, order._meta.model_name),
                                    args=(order.pk,))
                if request:
                    admin_abs = request.build_absolute_uri(admin_url)
                else:
                    site = getattr(settings, "SITE_URL", "")
                    admin_abs = urljoin(site, admin_url) if site else admin_url

                # Добавляем в сообщение (HTML). Заметьте: админ требует логина — ссылка будет работать только для авторизованных администраторов.
                lines.append(f'<a href="{escape(admin_abs)}">Открыть в админке</a>')
            except Exception:
                # безопасно игнорируем, если reverse не сработает
                pass

        # покупатель и контакт
        buyer = f"{order.last_name or ''} {order.first_name or ''}".strip() or "Гость"
        lines.append(f"Покупатель: {buyer}")
        if order.phone:
            lines.append(f"Тел: {order.phone}")
        if order.instagram:
            lines.append(f"Instagram: <a href='https://www.instagram.com/{order.instagram}/'>@{order.instagram}</a>")

        lines.append(f"Тип доставки: {order.get_delivery_type_display() if order.delivery_type else '—'}")
        lines.append(f"Способ оплаты: {order.get_payment_method_display() if order.payment_method else '—'}")
        lines.append(f"Итого: {order.total} руб.")

        # комментарий
        if getattr(order, "comment", None):
            lines.append("")
            lines.append(f"Комментарий: {order.comment}")

        text = "\n".join(lines)

        # отправляем через Bot API (используем parse_mode=HTML)
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        resp = requests.post(url, data=payload, timeout=6)
        if resp.status_code != 200:
            logger.error("Telegram notification failed: %s %s", resp.status_code, resp.text)

        # === 2. ОТПРАВЛЯЕМ КАРТИНКИ ТОВАРОВ ===
        send_products_as_album(chat_id, order, token)

    except Exception:
        logger.exception("Error while sending telegram notification for order %s", getattr(order, "pk", None))


def send_products_as_album(chat_id, order, token):
    import json
    import os
    from PIL import Image
    from io import BytesIO

    url = f"https://api.telegram.org/bot{token}/sendMediaGroup"
    order_items = order.items.select_related('product').all()

    if not order_items.exists():
        return

    media_list = []
    files = {}

    for idx, item in enumerate(order_items):
        product = item.product

        if not product.image or not product.image.name:
            continue

        try:
            image_path = product.image.path

            if not os.path.exists(image_path):
                logger.error(f"File not found: {image_path}")
                continue

            # ✅ Открываем и конвертируем в JPEG
            img = Image.open(image_path)

            # Если альфа-канал (PNG с прозрачностью) - добавляем белый фон
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Сохраняем в памяти как JPEG
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=85)
            img_io.seek(0)

            logger.info(f"[Album] Image converted: {image_path}")

            file_key = f"photo_{idx}"
            files[file_key] = img_io.getvalue()

            media_item = {
                "type": "photo",
                "media": f"attach://{file_key}",
                "caption": f"<b>{product.sizes.first()}</b>",
                "parse_mode": "HTML"
            }

            media_list.append(media_item)

        except Exception as e:
            logger.exception(f"Error processing {product.pk}: {e}")

    if not media_list:
        logger.error("[Album] No valid media items!")
        return

    try:
        logger.info(f"[Album] Sending {len(media_list)} photos...")

        response = requests.post(
            url,
            data={"chat_id": chat_id, "media": json.dumps(media_list)},
            files=files,
            timeout=30
        )

        if response.status_code == 200:
            logger.info(f"[Album] ✅ Success!")
        else:
            logger.error(f"[Album] ❌ {response.status_code}: {response.json()}")

    except Exception as e:
        logger.exception(f"[Album] ❌ Exception: {e}")