"""URL patterns for the store app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

from django.contrib.auth import views as auth_views

router = DefaultRouter()
router.register('products', views.ProductViewSet, basename='product')
router.register('cart', views.CartViewSet, basename='cart-api')

urlpatterns = [
    # Pages
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('cart/', views.cart_page, name='cart'),

    path('checkout/', views.checkout_view, name='checkout'),
    path("checkout/success/<uuid:public_id>/", views.checkout_success_view, name="checkout_success"),
    path("checkout/unavailable/", views.checkout_unavailable_view, name="checkout_unavailable"),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('account/', views.account_view, name='account'),
    path("account/addresses/", views.account_addresses_view, name="account_addresses"),
    path("account/account_orders/", views.account_orders_view, name="account_orders"),
path('account/orders/<uuid:public_id>/', views.account_order_detail_view, name='account_order_detail'),


    # Cart actions
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),

    # API
    # path('api/', include(router.urls)),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='store/password_reset_form.html',
        email_template_name='store/password_reset_email.txt',
        subject_template_name='store/password_reset_subject.txt',
        success_url='/password-reset/done/',
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='store/password_reset_done.html',
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='store/password_reset_confirm.html',
        success_url='/reset/done/',
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='store/password_reset_complete.html',
    ), name='password_reset_complete'),
]

urlpatterns += [
    path("api/", include("store.api.urls")),
]
