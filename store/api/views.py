from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Product, CartItem, SizeOption, FavoriteItem
from ..services.cart import get_or_create_cart
from .serializers import CartItemSerializer, FavoriteItemSerializer
from ..services.favorites import get_or_create_favorite


def cart_summary(cart):
    items = cart.items.select_related("product", "size").all()
    return {
        "items_count": items.count(),
        "total_qty": sum(i.quantity for i in items),
        "total_sum": float(sum(i.subtotal for i in items)),
    }


class CartRetrieveAPIView(APIView):
    def get(self, request):
        cart = get_or_create_cart(request)
        items = cart.items.select_related("product", "size").all()
        return Response({
            "items": CartItemSerializer(items, many=True, context={"request": request}).data,
            "summary": cart_summary(cart),
        })


class CartAddItemAPIView(APIView):
    """
    POST: product_id, qty=1, size_id(optional)
    """
    def post(self, request):
        cart = get_or_create_cart(request)

        product_id = request.data.get("product_id")
        qty = int(request.data.get("qty", 1) or 1)
        size_id = request.data.get("size_id")

        product = get_object_or_404(Product, id=product_id, is_active=True)
        size = None
        if size_id:
            size = SizeOption.objects.filter(id=size_id).first()

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            size=size,
            defaults={"quantity": qty},
        )
        if not created:
            item.quantity += qty
            item.save(update_fields=["quantity"])

        return Response({
            "ok": True,
            "item": CartItemSerializer(item, context={"request": request}).data,
            "summary": cart_summary(cart),
        }, status=status.HTTP_200_OK)


class CartSetQtyAPIView(APIView):
    """
    POST: item_id, qty
    """
    def post(self, request):
        cart = get_or_create_cart(request)
        item_id = request.data.get("item_id")
        qty = int(request.data.get("qty", 1) or 1)

        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        if qty < 1:
            item.delete()
        else:
            item.quantity = qty
            item.save(update_fields=["quantity"])

        return Response({"ok": True, "summary": cart_summary(cart)})


class CartRemoveItemAPIView(APIView):
    """
    POST: item_id
    """
    def post(self, request):
        cart = get_or_create_cart(request)
        item_id = request.data.get("item_id")
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()
        return Response({"ok": True, "summary": cart_summary(cart)})

def favorites_summary(fav):
    return {"count": fav.items.count()}

class FavoritesRetrieveAPIView(APIView):
    def get(self, request):
        fav = get_or_create_favorite(request)
        items = fav.items.select_related("product").all().order_by("-created_at")
        return Response({
            "items": FavoriteItemSerializer(items, many=True, context={"request": request}).data,
            "summary": favorites_summary(fav),
        })

class FavoritesToggleAPIView(APIView):
    """
    POST: product_id
    """
    def post(self, request):
        fav = get_or_create_favorite(request)
        product_id = request.data.get("product_id")
        product = get_object_or_404(Product, id=product_id, is_active=True)

        obj = FavoriteItem.objects.filter(favorite=fav, product=product).first()
        if obj:
            obj.delete()
            is_favorite = False
        else:
            FavoriteItem.objects.create(favorite=fav, product=product)
            is_favorite = True

        return Response({
            "ok": True,
            "is_favorite": is_favorite,
            "summary": favorites_summary(fav),
        }, status=status.HTTP_200_OK)

class UserStateAPIView(APIView):
    def get(self, request):
        cart = get_or_create_cart(request)
        fav = get_or_create_favorite(request)

        cart_product_ids = list(
            cart.items.values_list("product_id", flat=True).distinct()
        )
        favorite_ids = list(
            fav.items.values_list("product_id", flat=True)
        )

        return Response({
            "cart_product_ids": cart_product_ids,
            "favorite_ids": favorite_ids,
            "cart_summary": cart_summary(cart),
            "favorites_summary": favorites_summary(fav),
        })

class CartToggleAPIView(APIView):
    """
    POST: product_id
    Toggle: add (qty=1) or remove item for product (size=None).
    """
    def post(self, request):
        cart = get_or_create_cart(request)
        product_id = request.data.get("product_id")
        product = get_object_or_404(Product, id=product_id, is_active=True)

        item = CartItem.objects.filter(cart=cart, product=product, size__isnull=True).first()
        if item:
            item.delete()
            in_cart = False
        else:
            CartItem.objects.create(cart=cart, product=product, size=None, quantity=1)
            in_cart = True

        return Response({
            "ok": True,
            "in_cart": in_cart,
            "summary": cart_summary(cart),
        }, status=status.HTTP_200_OK)