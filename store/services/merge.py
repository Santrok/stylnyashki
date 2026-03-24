from django.db import transaction

from ..models import Cart, CartItem, Favorite, FavoriteItem


@transaction.atomic
def merge_cart_on_login(request, user):
    """
    Merge guest cart (session_key) into user cart on login/register.

    Rule: product is unique (and size if exists). If duplicate exists in user cart, guest item is dropped.
    """
    session_key = request.session.session_key
    if not session_key:
        return

    guest_cart = Cart.objects.filter(user__isnull=True, session_key=session_key).first()
    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    guest_items = guest_cart.items.select_related("product", "size").all()

    for gi in guest_items:
        exists = CartItem.objects.filter(
            cart=user_cart,
            product=gi.product,
            size=gi.size,
        ).exists()

        if not exists:
            gi.cart = user_cart
            gi.save(update_fields=["cart"])
        else:
            gi.delete()

    guest_cart.delete()


@transaction.atomic
def merge_favorites_on_login(request, user):
    """
    Merge guest favorite (session_key) into user favorite on login/register.

    Rule: product unique. If duplicate exists, guest item is dropped.
    """
    session_key = request.session.session_key
    if not session_key:
        return

    guest_fav = Favorite.objects.filter(user__isnull=True, session_key=session_key).first()
    if not guest_fav:
        return

    user_fav, _ = Favorite.objects.get_or_create(user=user)

    guest_items = guest_fav.items.select_related("product").all()

    for gi in guest_items:
        exists = FavoriteItem.objects.filter(
            favorite=user_fav,
            product=gi.product,
        ).exists()

        if not exists:
            gi.favorite = user_fav
            gi.save(update_fields=["favorite"])
        else:
            gi.delete()

    guest_fav.delete()