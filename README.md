# Стильняшки

Интернет-магазин детской и женской одежды на Django + Django REST Framework.

## Технологии

- Python 3.12+
- Django 6.x
- Django REST Framework 3.17+
- SQLite (разработка) / PostgreSQL (продакшн)
- Tailwind CSS (CDN)

## Быстрый старт

### 1. Клонировать репозиторий
```bash
git clone https://github.com/Santrok/stylnyashki.git
cd stylnyashki
```

### 2. Создать виртуальное окружение и установить зависимости
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Настроить переменные окружения
```bash
cp .env.example .env
# Откройте .env и при необходимости измените SECRET_KEY
```

### 4. Применить миграции
```bash
python manage.py migrate
```

### 5. Создать суперпользователя (для доступа к /admin/)
```bash
python manage.py createsuperuser
```

### 6. Запустить сервер разработки
```bash
python manage.py runserver
```

Сайт будет доступен по адресу: http://127.0.0.1:8000/

## Конфигурация для продакшна (PostgreSQL)

Добавьте в `.env`:

```
DEBUG=False
SECRET_KEY=<надёжный-секрет>
ALLOWED_HOSTS=your-domain.com

DB_NAME=stylnyashki
DB_USER=postgres
DB_PASSWORD=<пароль>
DB_HOST=localhost
DB_PORT=5432
```

## URL-структура

| URL | Описание |
|-----|----------|
| `/` | Главная страница |
| `/catalog/` | Каталог с фильтрами |
| `/cart/` | Корзина |
| `/checkout/` | Оформление заказа |
| `/account/` | Личный кабинет |
| `/login/` | Вход |
| `/register/` | Регистрация |
| `/logout/` | Выход |
| `/admin/` | Панель администратора |
| `/api/products/` | API: список товаров |
| `/api/products/{id}/` | API: детали товара |
| `/api/cart/` | API: корзина |
| `/api/cart/add/` | API: добавить товар |
| `/api/cart/{id}/remove/` | API: удалить товар |

## API примеры

```bash
# Список товаров
curl http://localhost:8000/api/products/

# Фильтрация
curl "http://localhost:8000/api/products/?category=Платья&season=Лето"

# Корзина
curl http://localhost:8000/api/cart/

# Добавить в корзину
curl -X POST http://localhost:8000/api/cart/add/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'
```
