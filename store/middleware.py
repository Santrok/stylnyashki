import base64

from django.utils.deprecation import MiddlewareMixin

from config.settings import BEPAID


class CustomAuthorizationMiddleware(MiddlewareMixin):
    """
    Middleware для обработки кастомной авторизации с использованием Basic Authentication.

    Проверяет заголовок 'HTTP_AUTHORIZATION', декодирует его и сверяет данные магазина (ID и секретный ключ).
    Если данные совпадают, заголовок удаляется, чтобы пропустить стандартную аутентификацию.
    """
    def process_request(self, request):
        """
        Обрабатывает запрос для проверки Basic Authentication.

        Если в заголовке 'HTTP_AUTHORIZATION' содержатся данные магазина, сверяет их с переменными окружения.
        При совпадении удаляет заголовок авторизации.

        Args:
            request (HttpRequest): Входящий HTTP-запрос.

        Returns:
            None: Если авторизация прошла успешно, заголовок удаляется.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if auth_header and 'Basic ' in auth_header:
            store_id = BEPAID.get('PAID_SERVICE_STORE_ID')
            secret_key = BEPAID.get('PAID_SERVICE_SECRET_KEY')

            encoded_credentials = auth_header.split(' ')[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            decoded_store_id, decoded_secret_key = decoded_credentials.split(':')

            if decoded_store_id == store_id and decoded_secret_key == secret_key:
                request.META.pop('HTTP_AUTHORIZATION', None)

        return None
