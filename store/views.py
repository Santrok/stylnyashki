import hashlib
import hmac
import json

from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from tools.telegram_notification import send_telegram_notification
import logging
from django.conf import settings
from datetime import timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Min, Max
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .forms import RegisterForm, LoginForm, AccountForm, PostalAddressForm, EuropostAddressForm, CheckoutForm, \
    ProductBulkForm, OrderStatusForm
from .models import Product, SizeOption, Cart, CartItem, Category, Address, Order, OrderItem, FavoriteItem, Payment, \
    SiteConfiguration
from .serializers import (
    ProductSerializer, ProductListSerializer,
    CartSerializer, CartItemSerializer,
)
from .services.favorites import get_or_create_favorite
from .services.payments import build_webpay_form_data
from .services.merge import merge_cart_on_login, merge_favorites_on_login
from .utils import _build_pagination_pages

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create_cart(request):
    """Return (or create) the Cart for the current user or anonymous session."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart



# ---------------------------------------------------------------------------
# Server-rendered page views
# ---------------------------------------------------------------------------

def home(request):
    """Render the home / landing page with featured products."""
    products = Product.objects.filter(is_active=True, status=Product.Status.AVAILABLE).order_by("?")[:8]

    context = {
        "products": products,
    }
    return render(request, 'store/home.html', context)


def catalog(request):
    base_qs = Product.objects.select_related("category").prefetch_related("sizes").filter(is_active=True, status=Product.Status.AVAILABLE)
    qs = base_qs

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q))

    category_slug = request.GET.get("category", "").strip()
    current_category = None
    current_root = None
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug).first()
        if current_category:
            current_root = current_category.get_root()
            qs = qs.filter(category__in=current_category.get_descendants(include_self=True))
        else:
            qs = qs.none()

    selected_sizes = request.GET.getlist("size")
    if selected_sizes:
        qs = qs.filter(sizes__value__in=selected_sizes).distinct()

    min_price = request.GET.get("min_price", "").strip()
    if min_price:
        try:
            qs = qs.filter(price__gte=float(min_price))
        except ValueError:
            pass

    max_price = request.GET.get("max_price", "").strip()
    if max_price:
        try:
            qs = qs.filter(price__lte=float(max_price))
        except ValueError:
            pass

    root_categories = Category.objects.filter(type="level_1").order_by("tree_id", "lft")

    price_stats = qs.aggregate(pmin=Min("price"), pmax=Max("price"))
    price_min = price_stats["pmin"]
    price_max = price_stats["pmax"]

    sizes = list(SizeOption.objects.all().order_by("sort", "value"))

    sort = request.GET.get("sort", "new").strip() or "new"
    sort_map = {
        "new": "-created_at",
        "price_asc": "price",
        "price_desc": "-price",
        "discount": "-discount",
    }
    order_by = sort_map.get(sort, "-created_at")

    breadcrumbs = []
    if current_category:
        breadcrumbs = list(current_category.get_ancestors(include_self=True))

    paginator = Paginator(qs.order_by(order_by), 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    pagination_pages = _build_pagination_pages(page_obj, window=2)

    return render(request, "store/catalog.html", {
        "products": page_obj.object_list,
        "page_obj": page_obj,
        "pagination_pages": pagination_pages,

        "root_categories": root_categories,
        "current_category": current_category,
        "current_root": current_root,
        "breadcrumbs": breadcrumbs,

        "selected_sizes": selected_sizes,
        "sizes": sizes,

        "price_min": price_min,
        "price_max": price_max,

        "sort": sort,
        "query_params": request.GET,
    })


def cart_page(request):
    """Render the shopping cart page."""
    cart = get_or_create_cart(request)

    # подгружаем позиции
    items = cart.items.select_related("product", "size")

    available_items = items.filter(availability=CartItem.Availability.AVAILABLE)

    # даже если quantity есть в модели, в UI не меняем, но сумму считать корректно
    total_qty = sum(i.quantity for i in available_items)
    total_sum = sum(i.subtotal for i in available_items)

    return render(request, 'store/cart.html', {
        'cart': cart,
        'items': items,
        'total_qty': total_qty,
        'total_sum': total_sum,
    })


def checkout_view(request):
    # Установка доступных способов оплаты
    cfg = cache.get("site_config_singleton")
    if cfg is None:
        cfg_obj = SiteConfiguration.get_solo()
        cfg = {
            "cod": bool(cfg_obj.payment_cod),
            "erip": bool(cfg_obj.payment_erip),
            "card": bool(cfg_obj.payment_card),
        }
        cache.set("site_config_singleton", cfg, 86400)
    available_payment_methods = cfg

    cart = get_or_create_cart(request)

    all_cart_items_qs = cart.items.select_related("product", "size").all()

    # Количество недоступных позиций в корзине (для показа подсказки)
    unavailable_count = all_cart_items_qs.exclude(
        availability=CartItem.Availability.AVAILABLE
    ).count()

    # Получаем список выбранных item-id (пришел из GET при переходе с корзины или из POST при финальном сабмите)
    # selected_ids = []
    # if request.method == "POST":
    #     selected_ids = request.POST.getlist("selected_items")
    # else:
    #     # GET
    #     selected_ids = request.GET.getlist("selected_items")
    selected_ids = request.GET.getlist("selected_items")

    try:
        selected_ids = [int(x) for x in selected_ids if x is not None and str(x).strip() != ""]
    except ValueError:
        selected_ids = []

    # Если есть выбранные id, используем их; иначе — все доступные позиции
    if selected_ids:
        # Только строки корзины, принадлежащие этой корзине
        selected_items_qs = cart.items.select_related("product", "size").filter(id__in=selected_ids)
        # Если ничего не найдено — перенаправляем на корзину с сообщением
        if not selected_items_qs.exists():
            messages.error(request, "Выбранные позиции не найдены в корзине.")
            return redirect("cart")

        # Если среди выбранных есть недоступные по availability — редиректим на страницу unavailable
        not_available_selected = selected_items_qs.exclude(availability=CartItem.Availability.AVAILABLE)


        if not_available_selected.exists():
            # пометим их RESERVED в корзинах и положим их product ids в сессию
            bad_product_ids = list(not_available_selected.values_list("product_id", flat=True))
            CartItem.objects.filter(product_id__in=bad_product_ids).update(
                availability=CartItem.Availability.RESERVED
            )
            request.session["checkout_unavailable_product_ids"] = bad_product_ids
            return redirect("checkout_unavailable")

        items_qs = selected_items_qs
    else:
        # No explicit selection — use ALL available items
        items_qs = cart.items.select_related("product", "size").filter(
            availability=CartItem.Availability.AVAILABLE
        )

    # Precompute totals from items_qs (these are the items we will attempt to checkout)
    items = list(items_qs)  # convert to list for iteration later
    total_qty = sum(i.quantity for i in items)
    total_sum = sum(i.subtotal for i in items)

    user = request.user if request.user.is_authenticated else None
    profile = getattr(user, "profile", None) if user else None

    # Сохранённые адреса
    post_addr = None
    ep_addr = None
    if user:
        post_addr = Address.objects.filter(user=user, type=Address.Type.POST).first()
        ep_addr = Address.objects.filter(user=user, type=Address.Type.EUROPOST).first()

    def build_initial():
        initial = {}

        if user:
            if user.first_name:
                initial["first_name"] = user.first_name
            if user.last_name:
                initial["last_name"] = user.last_name
            if user.email:
                initial["email"] = user.email

        if profile and getattr(profile, "phone", ""):
            initial["phone"] = profile.phone

        if profile and getattr(profile, "instagram_username", ""):
            initial["instagram"] = profile.instagram_username

        # middle_name priority: profile -> post_addr -> ep_addr
        if profile and getattr(profile, "middle_name", ""):
            initial["middle_name"] = profile.middle_name
        elif post_addr and getattr(post_addr, "middle_name", ""):
            initial["middle_name"] = post_addr.middle_name
        elif ep_addr and getattr(ep_addr, "middle_name", ""):
            initial["middle_name"] = ep_addr.middle_name

        # default delivery type: если есть только европочта — выбираем её
        initial["delivery_type"] = Order.DeliveryType.EUROPOST if (ep_addr and not post_addr) else Order.DeliveryType.POST

        initial["payment_method"] = Order.PaymentMethod.COD

        if post_addr:
            initial.update({
                "postal_index": post_addr.postal_index,
                "city": post_addr.city,
                "street": post_addr.street,
                "house": post_addr.house,
                "apartment": post_addr.apartment,
            })

        if ep_addr:
            initial.update({
                "europost_branch_number": ep_addr.europost_branch_number,
            })

        return initial

    # Если POST — final submit
    if request.method == "POST":
        form = CheckoutForm(request.POST, available_payment_methods=available_payment_methods)


        # Нечего оформлять
        if not items:
            if unavailable_count > 0:
                messages.error(request, "В корзине нет доступных товаров для оформления. Недоступные товары отмечены серым.")
            else:
                messages.error(request, "Корзина пуста. Добавьте товары, чтобы оформить заказ.")
            return redirect("cart")

        if form.is_valid():
            cd = form.cleaned_data
            delivery_price = Decimal("0.00")
            # products to lock: только те, которые принадлежали выбранным cart items
            product_ids = list({ci.product_id for ci in items})

            with transaction.atomic():
                now = timezone.now()
                reserve_until = now + timedelta(minutes=getattr(settings, "RESERVE_TTL_MINUTES", 60))

                # блокируем соответствующие продукты
                locked_products = (
                    Product.objects
                    .select_for_update()
                    .filter(id__in=product_ids)
                )

                # проверяем, не стали ли продукты RESERVED/SOLD/неактивны за время между показом и сабмитом
                unavailable_products_qs = locked_products.filter(
                    Q(status__in=[Product.Status.RESERVED, Product.Status.SOLD]) | Q(is_active=False)
                )
                if unavailable_products_qs.exists():
                    bad_ids = list(unavailable_products_qs.values_list("id", flat=True))
                    # отмечаем их серым у всех пользователей
                    CartItem.objects.filter(product_id__in=bad_ids).update(
                        availability=CartItem.Availability.RESERVED
                    )
                    # передаём их ids в сессию для страницы недоступности
                    request.session["checkout_unavailable_product_ids"] = bad_ids
                    return redirect("checkout_unavailable")

                # Все необходимые продукты доступны — создаём заказ
                order = Order.objects.create(
                    user=user if user else None,
                    status=Order.Status.NEW,
                    delivery_type=cd["delivery_type"],
                    payment_method=cd.get("payment_method", Order.PaymentMethod.COD),

                    first_name=cd["first_name"],
                    last_name=cd["last_name"],
                    middle_name=cd.get("middle_name", ""),
                    phone=cd["phone"],
                    instagram=cd.get("instagram", ""),
                    email=cd.get("email", ""),

                    postal_index=cd.get("postal_index", "") if cd["delivery_type"] == Order.DeliveryType.POST else "",
                    city=cd.get("city", "") if cd["delivery_type"] == Order.DeliveryType.POST else "",
                    street=cd.get("street", "") if cd["delivery_type"] == Order.DeliveryType.POST else "",
                    house=cd.get("house", "") if cd["delivery_type"] == Order.DeliveryType.POST else "",
                    apartment=cd.get("apartment", "") if cd["delivery_type"] == Order.DeliveryType.POST else "",

                    europost_branch_number=cd.get("europost_branch_number", "") if cd["delivery_type"] == Order.DeliveryType.EUROPOST else "",

                    comment=cd.get("comment", ""),
                    delivery_price=delivery_price,
                )

                # создаём OrderItem'ы только для выбранных cart items
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        product=ci.product,
                        size=ci.size,
                        product_name=ci.product.name,
                        price=ci.product.discounted_price,
                        quantity=ci.quantity,
                    )
                    for ci in items
                ])

                # резервируем продукты (меняем статус)
                locked_products.update(status=Product.Status.RESERVED, reserved_until=reserve_until)

                # Во всех корзинах помечаем эти товары серым RESERVED
                CartItem.objects.filter(product_id__in=product_ids).update(
                    availability=CartItem.Availability.RESERVED
                )

                # Удаляем выбранные позиции из текущей корзины
                if selected_ids:
                    cart.items.filter(id__in=selected_ids).delete()
                else:
                    # если selected_ids не было — удаляем все позиции, которые мы оформили (по product_ids)
                    cart.items.filter(product_id__in=product_ids).delete()

                # Пересчёт итогов заказа (если у тебя есть метод)
                order.recalc_totals(save=True)

                try:
                    transaction.on_commit(lambda: send_telegram_notification(order, request=request))
                except Exception:
                    # на всякий случай логируем; не мешаем оформлению заказа
                    logger.exception("Не удалось запланировать уведомление в Telegram для заказа. %s", order.pk)

                # раскомментировать при подключении оплаты картой
                # if cd.get("payment_method") == Order.PaymentMethod.CARD:
                #     payment = Payment.objects.create(
                #         order=order,
                #         gateway="webpay",
                #         amount=order.total,
                #         currency=settings.WEBPAY.get("CURRENCY", "BYN"),
                #         status=Payment.Status.PENDING,
                #     )
                #     return redirect("payment_create", payment_id=payment.pk)
                # else:
                #     return redirect("checkout_success", public_id=order.public_id)
                return redirect("checkout_success", public_id=order.public_id)
    else:
        form = CheckoutForm(initial=build_initial(), available_payment_methods=available_payment_methods)

    delivery_price = Decimal("0.00")
    total_with_delivery = total_sum + delivery_price

    # Передаём в шаблон selected_item_ids чтобы шаблон мог вставить скрытые поля для POST
    selected_item_ids = selected_ids

    return render(request, "store/checkout.html", {
        "form": form,
        "cart": cart,
        "items": items,  # выбранные (или все доступные) позиции для оформления
        "unavailable_count": unavailable_count,
        "total_qty": total_qty,
        "total_sum": total_sum,
        "delivery_price": delivery_price,
        "total_with_delivery": total_with_delivery,
        "selected_item_ids": selected_item_ids,
        "available_payment_methods": available_payment_methods,
    })


def payment_create_view(request, payment_id):
    """
    Рендерим страницу, которая auto-submit'ом отправляет форму на Webpay.
    """
    payment = get_object_or_404(Payment, pk=payment_id)
    # безопасная проверка: разрешаем редирект только если статус pending
    if payment.status != Payment.Status.PENDING:
        # уже обработанная попытка — перенаправляем на страницу статуса заказа
        return redirect("checkout_success", public_id=payment.order.public_id)

    form_data = build_webpay_form_data(payment)
    return render(request, "payments/redirect_to_webpay.html", {
        "payment_url": settings.WEBPAY["PAYMENT_URL"],
        "form_data": form_data,
    })


@csrf_exempt
def webpay_webhook(request):
    """
    Webhook от Webpay. Webpay POST'ит данные о платеже.
    Надо верифицировать подпись и обновить Payment + Order.
    ВНИМАНИЕ: формат и схема подписи — по документации Webpay. Здесь пример HMAC-SHA256.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid_json")

    # пример подписи в заголовке X-Signature (проверьте у Webpay)
    signature = request.META.get("HTTP_X_SIGNATURE") or request.GET.get("signature")
    if not signature:
        return HttpResponseBadRequest("missing_signature")

    # # Пример проверки HMAC-SHA256 от тела
    expected = hmac.new(settings.WEBPAY["SECRET_KEY"].encode("utf-8"), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return HttpResponseBadRequest("invalid_signature")

    # Пример полей (поменяйте под реальный webhook от Webpay)
    gw_payment_id = payload.get("payment_id") or payload.get("transaction_id")
    order_pub_id = payload.get("order_id")
    amount = payload.get("amount")
    status = payload.get("status")  # ожидаем 'paid' или подобное

    if not order_pub_id:
        return HttpResponseBadRequest("missing_order")

    try:
        order = Order.objects.get(public_id=order_pub_id)
    except Order.DoesNotExist:
        return HttpResponseBadRequest("unknown_order")

    # Находим запись Payment (по gateway_payment_id или по order / pending)
    payment = None
    if gw_payment_id:
        payment = Payment.objects.filter(gateway_payment_id=gw_payment_id).first()
    if not payment:
        # используем последний pending payment для этого заказа
        payment = Payment.objects.filter(order=order, status=Payment.Status.PENDING).order_by("-created_at").first()
        if payment and gw_payment_id:
            payment.gateway_payment_id = gw_payment_id
            payment.save(update_fields=["gateway_payment_id", "updated_at"])

    if not payment:
        return HttpResponseBadRequest("payment_not_found")

    # Сверяем сумму (строго)
    # Приведём к ��троке с двумя знаками
    try:
        if float(amount) != float(payment.amount):
            # логирование/уведомление - несоответствие суммы
            return HttpResponseBadRequest("amount_mismatch")
    except Exception:
        return HttpResponseBadRequest("amount_invalid")

    # Обрабатываем статус
    if status in ("paid", "success", "completed"):  # возможные варианты
        payment.mark_paid(payload=payload)
        return JsonResponse({"result": "ok"})
    else:
        payment.mark_failed(payload=payload)
        return JsonResponse({"result": "failed"})


def payment_return(request):
    """
    Return URL — пользователь возвращается сюда после оплаты (редирект со шлюза).
    Решающее слово за webhook; здесь мы просто показываем страницу ожидания/статуса.
    """
    order_id = request.GET.get("order_id") or request.GET.get("order")
    # если получен public_id, найдем заказ и покажем короткую страницу
    order = None
    if order_id:
        try:
            order = Order.objects.get(public_id=order_id)
        except Order.DoesNotExist:
            order = None
    return render(request, "payments/return.html", {"order": order})


def checkout_success_view(request, public_id):
    order = get_object_or_404(Order, public_id=public_id)
    return render(request, "store/checkout_success.html", {"order": order})

def checkout_unavailable_view(request):
    ids = request.session.pop("checkout_unavailable_product_ids", [])
    products = Product.objects.filter(id__in=ids).only("id", "name", "image", "status")
    return render(request, "store/checkout_unavailable.html", {
        "products": products,
    })


@login_required
def account_view(request):
    user = request.user
    profile = getattr(user, "profile", None)

    initial = {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": getattr(profile, "phone", "") if profile else "",
        "city": getattr(profile, "city", "") if profile else "",
        "instagram_username": getattr(profile, "instagram_username", "") if profile else "",
    }

    if request.method == "POST":
        form = AccountForm(request.POST, user=user)
        if form.is_valid():
            form.save()

            # безопасно “освежим” сессию
            update_session_auth_hash(request, request.user)

            messages.success(request, "Изменения сохранены.")
            return redirect("account")
    else:
        form = AccountForm(initial=initial, user=user)

    return render(request, "store/account.html", {"form": form})


@login_required
def account_addresses_view(request):
    user = request.user
    profile = getattr(user, "profile", None)

    postal_obj, _ = Address.objects.get_or_create(user=user, type=Address.Type.POST)
    ep_obj, _ = Address.objects.get_or_create(user=user, type=Address.Type.EUROPOST)

    # Автоподтягивание (ТОЛЬКО если в адресе пусто)
    def prefill_name_phone(obj: Address):
        changed = False

        if not obj.first_name and user.first_name:
            obj.first_name = user.first_name
            changed = True
        if not obj.last_name and user.last_name:
            obj.last_name = user.last_name
            changed = True
        if not obj.phone and profile and getattr(profile, "phone", ""):
            obj.phone = profile.phone
            changed = True

        if changed:
            obj.save(update_fields=["first_name", "last_name", "phone", "updated_at"])

    prefill_name_phone(postal_obj)
    prefill_name_phone(ep_obj)

    if request.method == "POST":
        if "save_post" in request.POST:
            post_form = PostalAddressForm(request.POST, instance=postal_obj, prefix="post")
            ep_form = EuropostAddressForm(instance=ep_obj, prefix="ep")

            if post_form.is_valid():
                obj = post_form.save(commit=False)
                obj.user = user
                obj.type = Address.Type.POST
                obj.save()
                messages.success(request, "Почтовый адрес сохранён.")
                return redirect("account_addresses")

        elif "save_ep" in request.POST:
            ep_form = EuropostAddressForm(request.POST, instance=ep_obj, prefix="ep")
            post_form = PostalAddressForm(instance=postal_obj, prefix="post")

            if ep_form.is_valid():
                obj = ep_form.save(commit=False)
                obj.user = user
                obj.type = Address.Type.EUROPOST
                obj.save()
                messages.success(request, "Адрес Европочты сохранён.")
                return redirect("account_addresses")
        else:
            # если нажали submit без имени — просто отрисуем обе формы с текущим instance
            post_form = PostalAddressForm(instance=postal_obj, prefix="post")
            ep_form = EuropostAddressForm(instance=ep_obj, prefix="ep")
    else:
        post_form = PostalAddressForm(instance=postal_obj, prefix="post")
        ep_form = EuropostAddressForm(instance=ep_obj, prefix="ep")

    return render(request, "store/account_addresses.html", {
        "post_form": post_form,
        "ep_form": ep_form,
    })


@login_required
def account_orders_view(request):
    """
    Список заказов пользователя с пагинацией.
    Показываем последние заказы первыми.
    """
    qs = (
        Order.objects
        .filter(user=request.user)
        .select_related('user')
        .order_by('-created_at')
    )

    # Пагинация: ?page=2
    paginator = Paginator(qs, 5)
    page = request.GET.get('page', 1)
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    return render(request, 'store/account_orders.html', {
        'orders_page': orders_page,
    })


@login_required
def account_order_detail_view(request, public_id):
    """
    Детальная страница заказа. Видна только владельцу.
    Показываем позиции, статус, дату, сумму, и если заказ отменён по причине "товар куплен" —
    даём пояснение и кнопки.
    """
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related(
            'items__product', 'items__size'
        ),
        public_id=public_id,
        user=request.user
    )

    # Подготовим флаг и список проблемных товаров, если заказ отменён
    problem_products = []
    if order.status == Order.Status.CANCELED:
        # Опционально: пометим товары, которые сейчас sold и стали причиной отмены
        product_ids = list(order.items.values_list('product_id', flat=True))
        sold_products = Product.objects.filter(id__in=product_ids, status=Product.Status.SOLD)
        problem_products = list(sold_products)

    return render(request, 'store/account_order_detail.html', {
        'order': order,
        'problem_products': problem_products,
    })


@login_required
def account_favorites_view(request):
    """
    Страница избранного в личном кабинете.
    Отображает элементы FavoriteItem, связанные с Favorite пользователя (get_or_create_favorite гарантирует наличие).
    """
    fav = get_or_create_favorite(request)  # для залогиненного вернёт Favorite.user = request.user
    items_qs = fav.items.select_related("product").order_by("-created_at")

    # Пагинация
    per_page = 12
    paginator = Paginator(items_qs, per_page)
    page = request.GET.get("page", 1)
    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)
    return render(request, "store/account_favorites.html", {
        "items_page": items_page,
    })


@login_required
@require_POST
def favorite_remove_view(request, item_id):
    """
    Удалить единицу FavoriteItem (по id) — безопасно, только если принадлежит текущему Favorite.
    """
    fav = get_or_create_favorite(request)
    fi = FavoriteItem.objects.filter(id=item_id, favorite=fav).first()
    if not fi:
        messages.error(request, "Позиция не найдена.")
        return redirect("account_favorites")

    fi.delete()
    messages.success(request, "Товар удалён из избранного.")
    # Возвращаем на ту же страницу (с учётом пагинации можно передать ?page=...)
    return redirect("account_favorites")


@login_required
@require_POST
def favorite_add_to_cart_view(request, item_id):
    """
    Добавляет продукт из избранного (FavoriteItem id) в корзину и удаляет элемент из избранного.
    Если товар недоступен — показываем ошибку.
    """
    fav = get_or_create_favorite(request)
    fi = get_object_or_404(FavoriteItem, id=item_id, favorite=fav)
    product = fi.product

    # Проверка доступности товара
    if not getattr(product, "is_active", True) or getattr(product, "status", None) == Product.Status.SOLD:
        messages.error(request, "К сожалению, этот товар недоступен для добавления в корзину.")
        # пометим позицию как удалённую из избранного (опционально) или пометим каким-то статусом — здесь просто оставим
        return redirect("account_favorites")

    cart = get_or_create_cart(request)

    # Пытаемся добавить в корзину:
    try:
        # Если у cart есть метод add_product( product, quantity, size )
        if hasattr(cart, "add_product"):
            cart.add_product(product=product, quantity=1)
        else:
            # Попробуем создать CartItem напрямую — подправь поля под свою модель CartItem
            CartItem.objects.create(cart=cart, product=product, quantity=1)
    except Exception:
        messages.error(request, "Не удалось добавить товар в корзину. Попробуйте ещё раз.")
        return redirect("account_favorites")

    # Удаляем элемент из избранного (т.к. добавили в корзину)
    fi.delete()
    messages.success(request, "Товар добавлен в корзину.")
    # Перенаправляем на корзину или остаёмся в избранном — здесь отправим на корзину
    return redirect("cart")



def _get_next_url(request, default='/account/'):
    next_url = request.POST.get('next') or request.GET.get('next') or default
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return default
    return next_url


def login_view(request):
    if request.user.is_authenticated:
        return redirect('account')

    if request.method == 'POST':
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            login(request, form.user)

            merge_cart_on_login(request, form.user)
            merge_favorites_on_login(request, form.user)

            return redirect(_get_next_url(request))
        # form.errors покажем в шаблоне
    else:
        form = LoginForm(request=request)

    return render(request, 'store/login.html', {
        'form': form,
        'next': _get_next_url(request),
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect('account')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            merge_cart_on_login(request, user)
            merge_favorites_on_login(request, user)

            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect(_get_next_url(request))
    else:
        form = RegisterForm()

    return render(request, 'store/register.html', {
        'form': form,
        'next': _get_next_url(request),
    })


def logout_view(request):
    logout(request)
    return redirect('home')


def cart_add(request, product_id):
    """Add a product to the cart (POST); redirect back to cart."""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = get_or_create_cart(request)
    size_id = request.POST.get('size_id')
    size = SizeOption.objects.filter(pk=size_id).first() if size_id else None
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, size=size)
    if not created:
        item.quantity += 1
        item.save()
    return redirect('cart')


def cart_remove(request, item_id):
    """Remove a cart item (POST); redirect back to cart."""
    cart = get_or_create_cart(request)
    CartItem.objects.filter(pk=item_id, cart=cart).delete()
    return redirect('cart')


# @staff_member_required
def products_bulk_upload_view(request):
    """
    Mobile-friendly bulk upload view (staff only).
    Expected POST (multipart/form-data):
      - name (required)
      - brand (optional)
      - category_id (optional)  -- integer id of Category
      - season (optional)
      - price (optional, decimal)
      - discount (optional)
      - is_active (optional, "1"/"on" means True)
      - status (optional; default available)
      - sizes[] (optional list of SizeOption ids)
      - images[] (multiple file inputs)
    For large uploads frontend should send files in batches (JS below does that).
    Returns JSON: {"created": n, "errors": [...]}
    """
    categories = Category.objects.all()[:200]
    sizes = SizeOption.objects.all()
    form = ProductBulkForm()
    return render(request, "store/account_products_bulk_upload.html", {"categories2": categories, "sizes": sizes, "form": form})

def staff_required_decorator(view_func):
    return user_passes_test(lambda u: u.is_active and u.is_staff)(view_func)

@method_decorator(staff_required_decorator, name='dispatch')
class AccountStaffOrdersListView(ListView):
    model = Order
    template_name = 'store/account_staff_orders_list.html'
    context_object_name = 'orders'   # object_list will be available as 'orders'
    paginate_by = 20
    # default ordering will be applied if no sort param provided

    def get_queryset(self):
        qs = Order.objects.select_related('user').all()
        q = (self.request.GET.get('q') or '').strip()
        status = self.request.GET.get('status') or ''
        delivery = self.request.GET.get('delivery') or ''
        date_from = self.request.GET.get('date_from') or ''
        date_to = self.request.GET.get('date_to') or ''
        sort = self.request.GET.get('sort') or 'created_desc'

        if q:
            if q.isdigit():
                # search by id OR by order_number if you prefer
                qs = qs.filter(Q(id=int(q)) | Q(order_number__icontains=q))
            else:
                qs = qs.filter(
                    Q(order_number__icontains=q) |
                    Q(user__email__icontains=q) |
                    Q(first_name__icontains=q) |
                    Q(last_name__icontains=q)
                )

        if status:
            qs = qs.filter(status=status)

        if delivery:
            qs = qs.filter(delivery_type=delivery)

        if date_from:
            d = parse_date(date_from)
            if d:
                qs = qs.filter(created_at__date__gte=d)
        if date_to:
            d = parse_date(date_to)
            if d:
                qs = qs.filter(created_at__date__lte=d)

        # sort mapping
        sort_map = {
            'created_desc': '-created_at',
            'created_asc': 'created_at',
            'total_desc': '-total',
            'total_asc': 'total',
            'status_asc': 'status',
            'status_desc': '-status',
        }
        order_by = sort_map.get(sort, '-created_at')
        qs = qs.order_by(order_by)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # keep compatibility with template which expects orders_page
        ctx['orders_page'] = ctx.get('page_obj')
        ctx['orders'] = ctx.get('orders') or ctx.get('object_list')

        # filters & choices for template
        ctx['status_choices'] = Order.Status.choices
        ctx['delivery_choices'] = Order.DeliveryType.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['delivery_filter'] = self.request.GET.get('delivery', '')
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')
        ctx['sort'] = self.request.GET.get('sort', 'created_desc')
        return ctx

@method_decorator(staff_required_decorator, name='dispatch')
class AccountStaffOrderDetailView(DetailView):
    model = Order
    template_name = 'store/account_staff_order_detail.html'   # файл шаблона ниже
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Status form for staff to change status via POST on this page
        ctx['status_form'] = OrderStatusForm(instance=self.object)
        # problem_products: пустой по умолчани��; при необходимости добавьте логику
        ctx['problem_products'] = []
        return ctx

@staff_required_decorator
@require_POST
def account_order_status_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    if new_status is None:
        return HttpResponseBadRequest('missing status')

    valid_vals = [c[0] for c in Order.Status.choices]
    if valid_vals and new_status not in valid_vals:
        return HttpResponseBadRequest('invalid status')

    old = order.status
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])

    # Return JSON for AJAX requests, otherwise redirect back to detail
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'order_id': order.pk, 'old': old, 'new': order.status})
    return redirect(reverse('account_staff_order_detail', args=[order.pk]))


# ---------------------------------------------------------------------------
# DRF API ViewSets
# ---------------------------------------------------------------------------

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for browsing products.

    list   – GET /api/products/
    detail – GET /api/products/{id}/
    """

    queryset = Product.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Use lightweight serializer for list, full serializer for detail."""
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        """Support filtering via query params: category, season, brand, q."""
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get('category'):
            qs = qs.filter(category=params['category'])
        if params.get('season'):
            qs = qs.filter(season=params['season'])
        if params.get('brand'):
            qs = qs.filter(brand=params['brand'])
        if params.get('q'):
            qs = qs.filter(Q(name__icontains=params['q']) | Q(brand__icontains=params['q']))
        return qs


class CartViewSet(viewsets.ViewSet):
    """
    API endpoint for cart management.

    GET    /api/cart/        – retrieve current cart
    POST   /api/cart/add/    – add item  {product_id, size_id?, quantity?}
    DELETE /api/cart/remove/{item_id}/ – remove item
    """

    def list(self, request):
        """Return the current user's (or session's) cart."""
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add a product to the cart. Body: {product_id, size_id?, quantity?}."""
        product_id = request.data.get('product_id')
        size_id = request.data.get('size_id')
        quantity = int(request.data.get('quantity', 1))

        product = get_object_or_404(Product, pk=product_id, is_active=True)
        cart = get_or_create_cart(request)
        size = SizeOption.objects.filter(pk=size_id).first() if size_id else None

        item, created = CartItem.objects.get_or_create(cart=cart, product=product, size=size)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

        return Response(CartItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Remove an item from the cart by item ID."""
        cart = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
