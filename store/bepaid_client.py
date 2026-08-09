"""
Клиент для интеграции с платёжной системой bePaid.
Документация: https://docs.bepaid.by/
"""
import base64
import hashlib
import json
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from requests.models import HTTPBasicAuth

logger = logging.getLogger(__name__)


class BepaidException(Exception):
    """Базовое исключение для ошибок bepaid."""
    pass


class BepaidAuthError(BepaidException):
    """Ошибка аутентификации/авторизации."""
    pass


class BepaidApiError(BepaidException):
    """Ошибка API bepaid."""
    pass


class BepaidWebhookError(BepaidException):
    """Ошибка при обработке вебхука."""
    pass


class BepaidClient:
    """
    Клиент для работы с API bepaid.
    Поддерживает создание платежей, проверку статуса и верификацию вебхуков.
    """

    def __init__(self):
        """Инициализация клиента с параметрами из settings.BEPAID."""
        bepaid_config = getattr(settings, "BEPAID", {})

        self.shop_id = bepaid_config.get("SHOP_ID", "")
        self.shop_secret = bepaid_config.get("SHOP_SECRET", "")
        self.api_url = bepaid_config.get("API_URL", "https://checkout.bepaid.by/ctp/api")
        self.public_key_pem = bepaid_config.get("PUBLIC_KEY", "")
        self.test_mode = bepaid_config.get("TEST_MODE", True)
        self.currency = bepaid_config.get("CURRENCY", "BYN")
        self.notification_url = bepaid_config.get("NOTIFICATION_URL", "")
        self.success_url = bepaid_config.get("SUCCESS_URL", "")
        self.decline_url = bepaid_config.get("DECLINE_URL", "")
        self.fail_url = bepaid_config.get("FAIL_URL", "")
        self.cancel_url = bepaid_config.get("CANCEL_URL", "")

        # Валидация обязательных параметров
        if not self.shop_id or not self.shop_secret:
            logger.warning(
                "Конфигурация BEPAID неполная: SHOP_ID или SHOP_SECRET не заданы"
            )

        # Загружаем публичный RSA ключ для верификации вебхуков
        self.public_key = self.public_key_pem
        # if self.public_key_pem:
        #     try:
        #         # Преобразуем экранированные переводы строк в реальные
        #         key_pem = self.public_key_pem.replace("\\n", "\n")
        #         self.public_key = serialization.load_pem_public_key(
        #             key_pem.encode(),
        #             backend=default_backend()
        #         )
        #         logger.debug("Публичный RSA-ключ успешно загружен")
        #     except Exception as e:
        #         logger.error(f"Ошибка при загрузке публичного RSA ключа: {e}")
        #         self.public_key = None
        # else:
        #     logger.warning("BEPAID PUBLIC_KEY не настроен")

    def _get_auth_header(self) -> Dict[str, str]:
        """
        Возвращает заголовок Authorization с Basic auth.
        """
        # credentials = f"{self.shop_id}:{self.shop_secret}"
        # encoded = base64.b64encode(credentials.encode()).decode()
        return {
            # "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Version": "2",
        }

    def _make_request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API bepaid.

        Args:
            method: HTTP метод (GET, POST)
            endpoint: Endpoint API (например, "checkouts")
            data: Данные для отправки (для POST)
            **kwargs: Дополнительные параметры для requests

        Returns:
            Распарсенный JSON ответ

        Raises:
            BepaidApiError: При ошибке API
        """
        url = f"{self.api_url}/{endpoint}"
        headers = self._get_auth_header()
        headers.update(kwargs.pop("headers", {}))

        try:
            if method == "POST":
                response = requests.post(
                    url,
                    json=data,
                    auth=HTTPBasicAuth(self.shop_id, self.shop_secret),
                    headers=headers,
                    timeout=30,
                    **kwargs
                )
            elif method == "GET":
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=30,
                    **kwargs
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            result = response.json()

            # Проверяем наличие ошибок в ответе
            if "errors" in result:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"Bepaid API error: {error_msg}")
                raise BepaidApiError(error_msg)

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Bepaid request error ({method} {endpoint}): {e}")
            raise BepaidApiError(f"Request failed: {str(e)}")

    def create_payment(
            self,
            order_id: str,
            amount: Decimal,
            description: str,
            customer_email: Optional[str] = None,
            customer_first_name: Optional[str] = None,
            customer_last_name: Optional[str] = None,
            customer_phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создаёт платёж (токен) в bepaid для оплаты картой.

        Args:
            order_id: Уникальный ID заказа в нашей системе (tracking_id)
            amount: Сумма платежа (Decimal, например Decimal("100.50"))
            description: Описание платежа
            customer_email: Email покупателя
            customer_first_name: Имя покупателя
            customer_last_name: Фамилия покупателя
            customer_phone: Телефон покупателя

        Returns:
            Dict с полями:
                - token: Токен платежа
                - redirect_url: URL для редиректа покупателя на форму оплаты

        Raises:
            BepaidApiError: При ошибке API
            BepaidException: При ошибке валидации данных
        """
        # Валидация данных
        if not order_id or not isinstance(order_id, str):
            raise BepaidException("order_id должен быть непустой строкой")
        if amount <= 0:
            raise BepaidException("Сумма должна быть больше 0")
        if not description:
            raise BepaidException("Требуется описание")

        # Преобразуем сумму в копейки (целые числа)
        amount_cents = int(amount * 100)

        payload = {
            "checkout": {
                "test": self.test_mode,
                "transaction_type": "payment",
                "attempts": 3,
                "settings": {
                    "notification_url": self.notification_url,
                    "success_url": self.success_url,
                    "decline_url": self.decline_url,
                    "fail_url": self.fail_url,
                    "cancel_url": self.cancel_url,
                    "language": "ru",
                    "button_next_text": "Вернуться в магазин",
                    "customer_fields": {
                        "read_only": ["email"],
                    },
                    "credit_card_fields": {
                        "read_only": ["holder"],
                    },
                },
                "order": {
                    "currency": self.currency,
                    "amount": amount_cents,
                    "description": description,
                    "tracking_id": order_id,
                },
                "customer": {
                    "email": customer_email,
                    "first_name": customer_first_name or "",
                    "last_name": customer_last_name or "",
                    "phone": customer_phone or "",
                },
                "payment_method": {
                    "types": ["credit_card"],
                },
            }
        }

        logger.info(
            f"Формирование bepaid оплаты: order_id={order_id}, amount={amount} {self.currency}"
        )

        response = self._make_request("POST", "checkouts", data=payload)

        # Распарсиваем ответ
        checkout = response.get("checkout", {})
        token = checkout.get("token")
        redirect_url = checkout.get("redirect_url")

        if not token or not redirect_url:
            logger.error(f"Некорректный ответ bepaid: {response}")
            raise BepaidApiError("Некорректный ответ: отсутствует token или redirect_url")

        logger.info(f"Платеж успешно создан: order_id={order_id}, token={token}")

        return {
            "token": token,
            "redirect_url": redirect_url,
        }

    def get_payment_status(self, token: str) -> Dict[str, Any]:
        """
        Получает статус платежа по токену.

        Args:
            token: Токен платежа, полученный при создании платежа

        Returns:
            Dict с информацией о платеже, включая:
                - status: Статус платежа (successful, failed, pending и т.д.)
                - finished: bool, завершен ли платёж
                - expired: bool, истёк ли срок оплаты
                - gateway_response: Ответ от платежной системы
                - order: Информация о заказе

        Raises:
            BepaidApiError: При ошибке API
        """
        if not token:
            raise BepaidException("Требуется token")

        logger.debug(f"Получение статуса платежа для token: {token}")

        response = self._make_request("GET", f"checkouts/{token}")

        checkout = response.get("checkout", {})
        status = checkout.get("status")
        finished = checkout.get("finished", False)
        expired = checkout.get("expired", False)

        logger.debug(
            f"Статус оплаты token {token}: status={status}, finished={finished}, expired={expired}"
        )

        return {
            "token": token,
            "status": status,
            "finished": finished,
            "expired": expired,
            "message": checkout.get("message", ""),
            "gateway_response": checkout.get("gateway_response", {}),
            "order": checkout.get("order", {}),
            "raw_response": checkout,
        }

    def verify_webhook_signature(self, payload_body: bytes, signature: str) -> bool:
        """
        Верифицирует подпись вебхука, используя публичный RSA ключ.

        Args:
            payload_body: Сырое тело запроса (bytes)
            signature: Значение из заголовка Content-Signature (base64-encoded)

        Returns:
            True если подпись корректна, False иначе

        Raises:
            BepaidWebhookError: При ошибке верификации
        """
        if not self.public_key:
            logger.error("Публичный ключ не сконфигурирован, нельзя проверить подпись вебхука")
            raise BepaidWebhookError("Публичный ключ не сконфигурирован")

        if not signature:
            logger.warning("Отсутствует подпись Webhook")
            return False

        try:
            # Декодируем подпись из base64
            signature_bytes = base64.b64decode(signature)

            # Вычисляем SHA256 хэш тела запроса
            payload_hash = hashlib.sha256(payload_body).digest()

            # Верифицируем подпись RSA
            self.public_key.verify(
                signature_bytes,
                payload_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            logger.info("Подпись Webhook успешно подтверждена")
            return True

        except Exception as e:
            logger.warning(f"Проверка подписи Webhook не удалась: {e}")
            return False

    def parse_webhook(
            self,
            payload_body: bytes,
            signature: Optional[str] = None,
            verify_signature: bool = True
    ) -> Dict[str, Any]:
        """
        Парсит и верифицирует вебхук от bepaid.

        Args:
            payload_body: Сырое тело POST запроса (bytes)
            signature: Значение из заголовка Content-Signature
            verify_signature: Проверять ли подпись (для продакшена обязательно True)

        Returns:
            Распарсенные данные вебхука

        Raises:
            BepaidWebhookError: При ошибке парсинга или верификации
        """
        # Верифицируем подпись если требуется
        if verify_signature:
            if not signature:
                raise BepaidWebhookError("Signature is required but not provided")
            if not self.verify_webhook_signature(payload_body, signature):
                raise BepaidWebhookError("Проверка подписи Webhook не удалась")

        # Парсим JSON
        try:
            webhook_data = json.loads(payload_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Не удалось спарсить тело Webhook: {e}")
            raise BepaidWebhookError(f"Неверный JSON в теле Webhook: {e}")

        # Извлекаем ключевые данные
        transaction = webhook_data.get("transaction", {})
        if not transaction:
            logger.error(
                f"Неверное тело webhook: отсутствуют данные транзакции. Полный: {webhook_data}"
            )
            raise BepaidWebhookError("Отсутствуют данные в Webhook")

        tracking_id = transaction.get("tracking_id")
        status = transaction.get("status")
        uid = transaction.get("uid")  # уникальный ID транзакции в bepaid
        amount = transaction.get("amount")
        currency = transaction.get("currency")
        message = transaction.get("message", "")

        if not tracking_id or not status:
            logger.error(
                f"Неверный Webhook: отсутствует tracking_id или статус. Данные: {transaction}"
            )
            raise BepaidWebhookError("Отсутствуют обязательные поля в данных транзакций")

        logger.info(
            f"Webhook parsed: tracking_id={tracking_id}, status={status}, uid={uid}, "
            f"amount={amount} {currency}"
        )

        return {
            "tracking_id": tracking_id,
            "status": status,
            "uid": uid,
            "amount": amount,
            "currency": currency,
            "message": message,
            "raw_transaction": transaction,
            "raw_webhook": webhook_data,
        }

    def map_status(self, bepaid_status: str) -> str:
        """
        Маппирует статус из bepaid на наши статусы Payment.

        Args:
            bepaid_status: Статус от bepaid (successful, failed, declined, pending и т.д.)

        Returns:
            Статус из Payment.Status (paid, failed, pending)
        """
        status_map = {
            "successful": "paid",
            "failed": "failed",
            "declined": "failed",  # отклонено банком = ошибка платежа
            "pending": "pending",
            "processing": "pending",
            "error": "failed",
        }

        return status_map.get(bepaid_status, "failed")


# Инстанс клиента для использования в других модулях
bepaid_client = BepaidClient()
