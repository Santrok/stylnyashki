import os
import time
import logging
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.text import slugify
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Product, CartItem, SizeOption, FavoriteItem, Category
from ..services.cart import get_or_create_cart
from .serializers import CartItemSerializer, FavoriteItemSerializer, BulkProductCommonSerializer
from ..services.favorites import get_or_create_favorite
from ..utils import convert_uploaded_image_to_avif_content
from ..tasks import process_product_image

MAX_FILE_SIZE = 12 * 1024 * 1024  # 12 MB per file limit on server side
MAX_FILES_PER_REQUEST = 50  # server accepts up to 50 files per request (client should batch)

# Logger
logger = logging.getLogger(__name__)  # либо "store.views.bulk_upload" если хотите явно

def cart_summary(cart):
    """
    Формирует краткую сводку корзины: количество позиций, общее количество и сумма.
    """
    items = cart.items.select_related("product", "size").all()
    return {
        "items_count": items.count(),
        "total_qty": sum(i.quantity for i in items),
        "total_sum": float(sum(i.subtotal for i in items)),
    }


class CartRetrieveAPIView(APIView):
    def get(self, request):
        cart = get_or_create_cart(request)
        items = cart.items.select_related("product", "size").all()
        return Response({
            "items": CartItemSerializer(items, many=True, context={"request": request}).data,
            "summary": cart_summary(cart),
        })


class CartAddItemAPIView(APIView):
    """
    POST: product_id, qty=1, size_id(optional)
    Добавляет товар в корзину или увеличивает количество, если позиция уже есть.
    """
    def post(self, request):
        cart = get_or_create_cart(request)

        product_id = request.data.get("product_id")
        qty = int(request.data.get("qty", 1) or 1)
        size_id = request.data.get("size_id")

        product = get_object_or_404(Product, id=product_id, is_active=True)
        size = None
        if size_id:
            size = SizeOption.objects.filter(id=size_id).first()

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            size=size,
            defaults={"quantity": qty},
        )
        if not created:
            item.quantity += qty
            item.save(update_fields=["quantity"])

        return Response({
            "ok": True,
            "item": CartItemSerializer(item, context={"request": request}).data,
            "summary": cart_summary(cart),
        }, status=status.HTTP_200_OK)


class CartSetQtyAPIView(APIView):
    """
    POST: item_id, qty
    Устанавливает количество для существующей позиции корзины, удаляет при qty < 1.
    """
    def post(self, request):
        cart = get_or_create_cart(request)
        item_id = request.data.get("item_id")
        qty = int(request.data.get("qty", 1) or 1)

        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        if qty < 1:
            item.delete()
        else:
            item.quantity = qty
            item.save(update_fields=["quantity"])

        return Response({"ok": True, "summary": cart_summary(cart)})


class CartRemoveItemAPIView(APIView):
    """
    POST: item_id
    Удаляет позицию из корзины.
    """
    def post(self, request):
        cart = get_or_create_cart(request)
        item_id = request.data.get("item_id")
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()
        return Response({"ok": True, "summary": cart_summary(cart)})


def favorites_summary(fav):
    """
    Возвращает краткую сводку избранного (количество элементов).
    """
    return {"count": fav.items.count()}


class FavoritesRetrieveAPIView(APIView):
    def get(self, request):
        fav = get_or_create_favorite(request)
        items = fav.items.select_related("product").all().order_by("-created_at")
        return Response({
            "items": FavoriteItemSerializer(items, many=True, context={"request": request}).data,
            "summary": favorites_summary(fav),
        })


class FavoritesToggleAPIView(APIView):
    """
    POST: product_id
    Переключает наличие товара в избранном: добавляет/удаляет.
    """
    def post(self, request):
        fav = get_or_create_favorite(request)
        product_id = request.data.get("product_id")
        product = get_object_or_404(Product, id=product_id, is_active=True)

        obj = FavoriteItem.objects.filter(favorite=fav, product=product).first()
        if obj:
            obj.delete()
            is_favorite = False
        else:
            FavoriteItem.objects.create(favorite=fav, product=product)
            is_favorite = True

        return Response({
            "ok": True,
            "is_favorite": is_favorite,
            "summary": favorites_summary(fav),
        }, status=status.HTTP_200_OK)


class UserStateAPIView(APIView):
    """
    Возвращает состояние пользователя: продукты в корзине, избранное и их сводки.
    """
    def get(self, request):
        cart = get_or_create_cart(request)
        fav = get_or_create_favorite(request)

        cart_product_ids = list(
            cart.items.values_list("product_id", flat=True).distinct()
        )
        favorite_ids = list(
            fav.items.values_list("product_id", flat=True)
        )

        return Response({
            "cart_product_ids": cart_product_ids,
            "favorite_ids": favorite_ids,
            "cart_summary": cart_summary(cart),
            "favorites_summary": favorites_summary(fav),
        })


class CartToggleAPIView(APIView):
    """
    POST: product_id
    Переключатель: если товар (без размера) в корзине — удаляет, иначе — добавляет (qty=1).
    """
    def post(self, request):
        cart = get_or_create_cart(request)
        product_id = request.data.get("product_id")
        product = get_object_or_404(Product, id=product_id, is_active=True)

        item = CartItem.objects.filter(cart=cart, product=product, size__isnull=True).first()
        if item:
            item.delete()
            in_cart = False
        else:
            CartItem.objects.create(cart=cart, product=product, size=None, quantity=1)
            in_cart = True

        return Response({
            "ok": True,
            "in_cart": in_cart,
            "summary": cart_summary(cart),
        }, status=status.HTTP_200_OK)


class BulkProductUploadAPIView(APIView):
    """
    API для пакетной загрузки товаров (bulk upload).
    Принимает multipart/form-data с полями, описанными в BulkProductCommonSerializer и списком файлов 'images'.
    Вместо синхронной конвертации изображений, сохраняет файлы во временный каталог в storage и ставит задачу Celery,
    которая выполнит конвертацию в фоне и сохранит avif в поле Product.image.
    В ответ возвращаем созданные product_id и task_id для каждой задачи.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (IsAdminUser,)

    def post(self, request, format=None):
        # Валидируем общие поля через сериализатор
        serializer = BulkProductCommonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        images = request.FILES.getlist("images")
        if not images:
            logger.warning(
                "Попытка пакетной загрузки без файлов. Пользователь id=%s",
                getattr(request.user, 'pk', None)
            )
            return Response(
                {"created": 0, "errors": ["No image files provided under 'images'"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(images) > MAX_FILES_PER_REQUEST:
            logger.warning(
                "Попытка пакетной загрузки с превышением количества файлов: %d (пользователь id=%s)",
                len(images),
                getattr(request.user, 'pk', None)
            )
            return Response(
                {"created": 0, "errors": [f"Too many files in one request; max {MAX_FILES_PER_REQUEST} allowed"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Разрешаем категорию, если передана
        category = None
        if data.get("category_id"):
            try:
                category = Category.objects.get(pk=int(data["category_id"]))
            except Category.DoesNotExist:
                logger.warning(
                    "Bulk upload: категория с id=%s не найдена (пользователь id=%s)",
                    data.get("category_id"),
                    getattr(request.user, 'pk', None)
                )
                return Response(
                    {"created": 0, "errors": [f"Category id {data['category_id']} not found"]},
                    status=status.HTTP_400_BAD_REQUEST
                )

        sizes_qs = SizeOption.objects.filter(id__in=data.get("sizes", [])) if data.get("sizes") else None

        created_ids = []
        errors = []
        tasks = []
        base_safe = slugify(data["name"]) or "product"
        timestamp = int(time.time())

        logger.info(
            "Начало пакетной загрузки: пользователь id=%s, файлов=%d, имя товара='%s'",
            getattr(request.user, 'pk', None),
            len(images),
            data.get("name")
        )

        tmp_dir = getattr(settings, "BULK_UPLOAD_TMP_DIR", "bulk_tmp")

        for idx, uploaded in enumerate(images):
            p = None
            try:
                logger.info(
                    "Обработка файла: индекс=%d, имя=%s (enqueue task)",
                    idx,
                    getattr(uploaded, "name", None)
                )

                # Проверка размера файла
                if hasattr(uploaded, "size") and uploaded.size and uploaded.size > MAX_FILE_SIZE:
                    logger.warning(
                        "Файл '%s' превышает допустимый размер (%d байт). Пропуск.",
                        getattr(uploaded, "name", ""),
                        MAX_FILE_SIZE
                    )
                    raise ValueError(f"File '{uploaded.name}' exceeds max file size ({MAX_FILE_SIZE} bytes)")

                # Подготовка полей продукта
                price_val = data.get("price")
                if price_val is None:
                    price_val = Product._meta.get_field("price").get_default()
                else:
                    price_val = Decimal(price_val)

                # Создаём продукт без изображения (image заполним в фоне)
                p = Product.objects.create(
                    name=data["name"],
                    brand=data.get("brand"),
                    category=category,
                    season=data.get("season"),
                    price=price_val,
                    discount=int(data.get("discount", 0)) if data.get("discount") is not None else 0,
                    is_active=bool(data.get("is_active", True)),
                    status=data.get("status", Product.Status.AVAILABLE),
                )

                if sizes_qs:
                    p.sizes.set(sizes_qs)

                # Сохраняем загруженный файл временно в storage (media/bulk_tmp/...)
                unique_prefix = uuid4().hex
                safe_name = f"{unique_prefix}_{uploaded.name}"
                storage_path = f"{tmp_dir}/{safe_name}"

                saved_path = default_storage.save(storage_path, uploaded)
                logger.debug("Временный файл сохранён: %s (product_id=%s)", saved_path, p.pk)

                # Запускаем фоновую задачу на обработку изображения
                filename_base = f"{base_safe}-{timestamp}-{idx}"
                task = process_product_image.delay(saved_path, p.pk, filename_base)

                tasks.append({"product_id": p.pk, "task_id": task.id})
                created_ids.append(p.pk)

                logger.info("Создан продукт id=%s и поставлена задача %s для файла %s", p.pk, task.id, getattr(uploaded, "name", None))

            except Exception as exc:
                # Логируем исключение с трассировкой
                logger.exception(
                    "Ошибка при обработке файла: индекс=%s, имя=%s, ошибка=%s",
                    idx,
                    getattr(uploaded, "name", None),
                    str(exc)
                )
                # Пытаемся удалить частично созданный объект, если он есть
                try:
                    if p and getattr(p, "pk", None):
                        p.delete()
                except Exception:
                    logger.exception(
                        "Не удалось удалить частично созданный объект для файла: индекс=%s, имя=%s",
                        idx,
                        getattr(uploaded, "name", None)
                    )
                errors.append({"index": idx, "filename": getattr(uploaded, "name", ""), "error": str(exc)})

        logger.info(
            "Пакетная загрузка завершена (enqueue): пользователь id=%s, создано=%d задач=%d, ошибок=%d",
            getattr(request.user, 'pk', None),
            len(created_ids),
            len(tasks),
            len(errors)
        )

        return Response(
            {"created": len(created_ids), "created_ids": created_ids, "tasks": tasks, "errors": errors},
            status=status.HTTP_200_OK
        )