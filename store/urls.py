"""URL patterns for the store app."""

from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from django.contrib.auth import views as auth_views

from .views import ProductViewSet, CartViewSet, home, catalog, cart_page, checkout_view, checkout_success_view, \
    checkout_unavailable_view, login_view, register_view, logout_view, account_addresses_view, account_view, \
    account_orders_view, account_order_detail_view, account_favorites_view, favorite_remove_view, \
    favorite_add_to_cart_view, products_bulk_upload_view, AccountStaffOrdersListView, AccountStaffOrderDetailView, \
    account_order_status_update, cart_add, cart_remove

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('cart', CartViewSet, basename='cart-api')

urlpatterns = [
    # Pages
    path('', home, name='home'),
    path('catalog/', catalog, name='catalog'),
    path('cart/', cart_page, name='cart'),

    path('checkout/', checkout_view, name='checkout'),
    path("checkout/success/<uuid:public_id>/", checkout_success_view, name="checkout_success"),
    path("checkout/unavailable/", checkout_unavailable_view, name="checkout_unavailable"),

    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),

    path('account/', account_view, name='account'),
    path("account/addresses/", account_addresses_view, name="account_addresses"),
    path("account/account_orders/", account_orders_view, name="account_orders"),
    path('account/orders/<uuid:public_id>/', account_order_detail_view, name='account_order_detail'),
    path('account/favorites/', account_favorites_view, name='account_favorites'),
    path('account/favorites/remove/<int:item_id>/', favorite_remove_view, name='favorite_remove'),
    path('account/favorites/add-to-cart/<int:item_id>/', favorite_add_to_cart_view, name='favorite_add_to_cart'),
    path('account/products/bulk-upload/', products_bulk_upload_view, name='account_product'),
    path('account/staff/orders/', AccountStaffOrdersListView.as_view(), name='account_staff_orders_list'),
    path('account/staff/orders/<int:pk>/', AccountStaffOrderDetailView.as_view(),
         name='account_staff_order_detail'),
    path('account/staff/orders/<int:pk>/status/', account_order_status_update,
         name='account_staff_order_status_update'),

    # Cart actions
    path('cart/add/<int:product_id>/', cart_add, name='cart_add'),
    path('cart/remove/<int:item_id>/', cart_remove, name='cart_remove'),

    path('cookie-settings/', TemplateView.as_view(template_name='cookie_settings.html'), name='cookie_settings'),
    path('privacy/', TemplateView.as_view(template_name='privacy_policy.html'), name='privacy'),
    path('public_offer/', TemplateView.as_view(template_name='public_offer.html'), name='public_offer'),
    path('how_to_order/', TemplateView.as_view(template_name='how_to_order.html'), name='how_to_order'),

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
