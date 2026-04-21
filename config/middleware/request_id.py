import uuid
import threading
from django.utils.deprecation import MiddlewareMixin
from ..logging_filters import _request_local

class RequestIDMiddleware(MiddlewareMixin):
    """
    Простая middleware, которая добавляет request_id в threadlocal для логирования.
    """
    def process_request(self, request):
        rid = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        _request_local.request_id = rid
        request.request_id = rid

    def process_response(self, request, response):
        # очистка
        if hasattr(_request_local, "request_id"):
            try:
                del _request_local.request_id
            except Exception:
                pass
        # пробрассываем X-Request-Id в ответ, полезно для трассировки
        if hasattr(request, "request_id") and request.request_id:
            response["X-Request-Id"] = request.request_id
        return response