from .models import Category
from .services.cart import get_or_create_cart
from .services.favorites import get_or_create_favorite


def header_counts(request):
    """
    SSR бейджи в шапке.
    cart_count = суммарное количество (qty)
    favorites_count = количество избранных товаров
    """
    try:
        cart = get_or_create_cart(request)
        items = cart.items.all()
        cart_count = sum(i.quantity for i in items)

        fav = get_or_create_favorite(request)
        favorites_count = fav.items.count()
    except Exception:
        # чтобы шапка не падала, если миграции/таблицы еще не готовы
        cart_count = 0
        favorites_count = 0

    return {
        "cart_count": cart_count,
        "favorites_count": favorites_count,
    }

def header_categories(request):
    categories = Category.objects.filter(level=0)
    return {
        "categories": categories,
    }