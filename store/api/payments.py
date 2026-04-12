from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, throttling
from django.shortcuts import get_object_or_404
from django.conf import settings
from ..models import Order, Payment
from django.urls import reverse


class PaymentStatusAPIView(APIView):
    """
    GET /api/payments/status/?order_id=<public_id> OR ?payment_id=<pk>
    Публичный endpoint, возвращает текущий статус оплаты для polling.
    """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (throttling.AnonRateThrottle, throttling.UserRateThrottle)

    def get(self, request, *args, **kwargs):
        payment_pk = request.query_params.get("payment_id")
        order_pub = request.query_params.get("order_id")

        payment = None
        order = None

        if payment_pk:
            try:
                payment = Payment.objects.select_related("order").get(pk=int(payment_pk))
                order = payment.order
            except (Payment.DoesNotExist, ValueError):
                return Response({"error": "payment_not_found"}, status=status.HTTP_404_NOT_FOUND)
        elif order_pub:
            try:
                order = Order.objects.get(public_id=order_pub)
            except Order.DoesNotExist:
                return Response({"error": "order_not_found"}, status=status.HTTP_404_NOT_FOUND)
            payment = order.payments.order_by("-created_at").first()
        else:
            return Response({"error": "missing_parameters"}, status=status.HTTP_400_BAD_REQUEST)

        resp = {
            "status": (payment.status if payment else order.payment_status),
            "payment_id": (payment.pk if payment else None),
            "order_public_id": str(order.public_id) if order else None,
            "message": "",
        }

        if payment:
            if payment.status == Payment.Status.PENDING:
                resp["message"] = "Ожидается оплата"
            elif payment.status == Payment.Status.PAID:
                resp["message"] = "Платёж получен"
            elif payment.status == Payment.Status.FAILED:
                resp["message"] = "Платёж не пройден"
            else:
                resp["message"] = payment.status
        else:
            resp["message"] = "Ожидается оплата" if order.payment_status == Order.PaymentStatus.PENDING else order.payment_status

        return Response(resp, status=status.HTTP_200_OK)


class RetryThrottle(throttling.UserRateThrottle):
    scope = 'retry'
    # rate for 'retry' must be defined in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']


@method_decorator(csrf_exempt, name='dispatch')  # позволяeм анонимный POST с token (без CSRF)
class PaymentRetryAPIView(APIView):
    """
    POST /api/payments/retry/<order_public_id>/
    Позволяет:
     - авторизованному пользователю (владельцу заказа) создать новую попытку оплаты;
     - анонимному пользователю — при предоставлении валидного одноразового token (order.retry_token).
    Возвращает: { payment_create_url, payment_id }
    """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (RetryThrottle,)

    def post(self, request, order_public_id, *args, **kwargs):
        order = get_object_or_404(Order, public_id=order_public_id)

        # Вариант 1: залогиненный пользователь должен быть владельцем заказа
        if request.user.is_authenticated:
            if not order.user or request.user != order.user:
                return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        # Вариант 2: анонимный пользователь — должен предоставить token (в body или GET)
        else:
            token = None
            # принимаем как JSON body token или query param
            if isinstance(request.data, dict):
                token = request.data.get("token") or request.query_params.get("token")
            else:
                token = request.query_params.get("token")
            if not token:
                return Response({"error": "token_required"}, status=status.HTTP_403_FORBIDDEN)
            try:
                # сравниваем строки (order.retry_token — UUID)
                if str(order.retry_token) != str(token):
                    return Response({"error": "invalid_token"}, status=status.HTTP_403_FORBIDDEN)
            except Exception:
                return Response({"error": "invalid_token"}, status=status.HTTP_403_FORBIDDEN)

        # Запрещаем retry для отменённых заказов
        if order.status == Order.Status.CANCELED:
            return Response({"error": "order_canceled"}, status=status.HTTP_400_BAD_REQUEST)

        # Создаём новую запись Payment
        payment = Payment.objects.create(
            order=order,
            gateway="webpay",
            amount=order.total,
            currency=settings.WEBPAY.get("CURRENCY", "BYN"),
            status=Payment.Status.PENDING,
        )

        payment_create_url = reverse("payment_create", args=[payment.pk])
        return Response({"payment_create_url": payment_create_url, "payment_id": payment.pk}, status=status.HTTP_201_CREATED)