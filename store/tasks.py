
from __future__ import absolute_import, unicode_literals
import logging
import os
from uuid import uuid4
from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings

from .models import Product
from .utils import convert_uploaded_image_to_avif_content

logger = logging.getLogger("store.tasks")

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