import threading
import logging

_request_local = threading.local()

def get_request_id(default=""):
    return getattr(_request_local, "request_id", default)

class RequestIDFilter(logging.Filter):
    """
    Добавляет request_id в LogRecord (можно установить через middleware).
    """
    def filter(self, record):
        record.request_id = get_request_id()
        return True

# Экспорт класса под именем, которое использовали в settings.LOGGING
RequestIDFilter = RequestIDFilter