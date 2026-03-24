from django.urls import path
from . import views

urlpatterns = [
    path("cart/", views.CartRetrieveAPIView.as_view(), name="api_cart"),
    path("cart/add/", views.CartAddItemAPIView.as_view(), name="api_cart_add"),
    path("cart/set-qty/", views.CartSetQtyAPIView.as_view(), name="api_cart_set_qty"),
    path("cart/remove/", views.CartRemoveItemAPIView.as_view(), name="api_cart_remove"),

    path("favorites/", views.FavoritesRetrieveAPIView.as_view(), name="api_favorites"),
    path("favorites/toggle/", views.FavoritesToggleAPIView.as_view(), name="api_favorites_toggle"),

    path("state/", views.UserStateAPIView.as_view(), name="api_state"),
    path("cart/toggle/", views.CartToggleAPIView.as_view(), name="api_cart_toggle")
]
