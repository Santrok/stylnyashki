import os
from io import BytesIO

from PIL import Image
from django.core.files.base import ContentFile
import pillow_avif  # Необходимо для преобразования изображений в avif


def _build_pagination_pages(page_obj, window=2):
    """
    Возвращает список элементов для пагинации.
    Числа = номера страниц, None = троеточие.
    """
    total = page_obj.paginator.num_pages
    current = page_obj.number

    if total <= 1:
        return []

    pages = {1, total}
    for p in range(current - window, current + window + 1):
        if 1 <= p <= total:
            pages.add(p)

    pages = sorted(pages)

    result = []
    prev = None
    for p in pages:
        if prev is not None and p - prev > 1:
            result.append(None)  # "..."
        result.append(p)
        prev = p
    return result


def convert_image_to_avif(photo):
    """
    Конвертирует все форматы фото в avif
    """

    # Открываем загруженный файл с помощью Pillow
    img = Image.open(photo)

    # Создаём временный буфер для сохранения изображения в формате AVIF
    img_io = BytesIO()

    # Сохраняем изображение в формате AVIF
    img.save(img_io, format='AVIF')

    # Перематываем буфер обратно в начало
    img_io.seek(0)

    # Генерируем новое имя файла с расширением .avif
    new_filename = os.path.splitext(photo.name)[0] + '.avif'

    # Обновляем файл в поле photo с новым расширением
    photo.save(new_filename, ContentFile(img_io.read()), save=False)