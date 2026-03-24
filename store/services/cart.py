from ..models import Cart


def ensure_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    session_key = ensure_session_key(request)
    cart, _ = Cart.objects.get_or_create(user=None, session_key=session_key)
    return cart