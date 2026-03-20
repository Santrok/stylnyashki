"""
Views for the Стильняшки store.

Includes:
- Server-rendered page views (home, catalog, cart, checkout, account, auth)
- DRF API viewsets (products, cart)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Product, SizeOption, Cart, CartItem
from .serializers import (
    ProductSerializer, ProductListSerializer,
    CartSerializer, CartItemSerializer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create_cart(request):
    """Return (or create) the Cart for the current user or anonymous session."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


# ---------------------------------------------------------------------------
# Server-rendered page views
# ---------------------------------------------------------------------------

def home(request):
    """Render the home / landing page with featured products."""
    featured = Product.objects.filter(is_active=True)[:8]
    return render(request, 'store/home.html', {'featured': featured})


def catalog(request):
    """
    Render the product catalogue with optional GET-param filtering.

    Supported query params:
        q        – text search in name/brand
        category – exact category match
        season   – exact season match
        brand    – exact brand match
        min_price / max_price – price range
    """
    qs = Product.objects.filter(is_active=True)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q))

    category = request.GET.get('category', '').strip()
    if category:
        qs = qs.filter(category=category)

    season = request.GET.get('season', '').strip()
    if season:
        qs = qs.filter(season=season)

    brand = request.GET.get('brand', '').strip()
    if brand:
        qs = qs.filter(brand=brand)

    min_price = request.GET.get('min_price', '').strip()
    if min_price:
        try:
            qs = qs.filter(price__gte=float(min_price))
        except ValueError:
            pass

    max_price = request.GET.get('max_price', '').strip()
    if max_price:
        try:
            qs = qs.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # Build filter choice lists for the sidebar
    categories = Product.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    seasons = Product.objects.filter(is_active=True).values_list('season', flat=True).distinct()
    brands = Product.objects.filter(is_active=True).values_list('brand', flat=True).distinct()

    return render(request, 'store/catalog.html', {
        'products': qs,
        'categories': [c for c in categories if c],
        'seasons': [s for s in seasons if s],
        'brands': [b for b in brands if b],
        'query_params': request.GET,
    })


def cart_page(request):
    """Render the shopping cart page."""
    cart = get_or_create_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})


@login_required
def checkout(request):
    """Render the checkout page (requires login)."""
    cart = get_or_create_cart(request)
    if request.method == 'POST':
        # Stub: clear cart and show success
        cart.items.all().delete()
        messages.success(request, 'Заказ оформлен! Спасибо за покупку.')
        return redirect('home')
    return render(request, 'store/checkout.html', {'cart': cart})


@login_required
def account(request):
    """Render the user account / profile page."""
    return render(request, 'store/account.html', {'user': request.user})


def login_view(request):
    """Handle GET (show form) and POST (authenticate) for the login page."""
    if request.user.is_authenticated:
        return redirect('account')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/account/')
            return redirect(next_url)
        messages.error(request, 'Неверный логин или пароль.')
    return render(request, 'store/login.html')


def register_view(request):
    """Handle GET (show form) and POST (create account) for the register page."""
    if request.user.is_authenticated:
        return redirect('account')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if password1 != password2:
            messages.error(request, 'Пароли не совпадают.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            messages.success(request, f'Добро пожаловать, {username}!')
            return redirect('account')
    return render(request, 'store/register.html')


def logout_view(request):
    """Log the user out and redirect to home."""
    logout(request)
    return redirect('home')


# ---------------------------------------------------------------------------
# Cart actions (non-API)
# ---------------------------------------------------------------------------

def cart_add(request, product_id):
    """Add a product to the cart (POST); redirect back to cart."""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = get_or_create_cart(request)
    size_id = request.POST.get('size_id')
    size = SizeOption.objects.filter(pk=size_id).first() if size_id else None
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, size=size)
    if not created:
        item.quantity += 1
        item.save()
    return redirect('cart')


def cart_remove(request, item_id):
    """Remove a cart item (POST); redirect back to cart."""
    cart = get_or_create_cart(request)
    CartItem.objects.filter(pk=item_id, cart=cart).delete()
    return redirect('cart')


# ---------------------------------------------------------------------------
# DRF API ViewSets
# ---------------------------------------------------------------------------

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for browsing products.

    list   – GET /api/products/
    detail – GET /api/products/{id}/
    """

    queryset = Product.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Use lightweight serializer for list, full serializer for detail."""
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        """Support filtering via query params: category, season, brand, q."""
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get('category'):
            qs = qs.filter(category=params['category'])
        if params.get('season'):
            qs = qs.filter(season=params['season'])
        if params.get('brand'):
            qs = qs.filter(brand=params['brand'])
        if params.get('q'):
            qs = qs.filter(Q(name__icontains=params['q']) | Q(brand__icontains=params['q']))
        return qs


class CartViewSet(viewsets.ViewSet):
    """
    API endpoint for cart management.

    GET    /api/cart/        – retrieve current cart
    POST   /api/cart/add/    – add item  {product_id, size_id?, quantity?}
    DELETE /api/cart/remove/{item_id}/ – remove item
    """

    def list(self, request):
        """Return the current user's (or session's) cart."""
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add a product to the cart. Body: {product_id, size_id?, quantity?}."""
        product_id = request.data.get('product_id')
        size_id = request.data.get('size_id')
        quantity = int(request.data.get('quantity', 1))

        product = get_object_or_404(Product, pk=product_id, is_active=True)
        cart = get_or_create_cart(request)
        size = SizeOption.objects.filter(pk=size_id).first() if size_id else None

        item, created = CartItem.objects.get_or_create(cart=cart, product=product, size=size)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

        return Response(CartItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Remove an item from the cart by item ID."""
        cart = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
