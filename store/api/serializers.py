from rest_framework import serializers

from ..models import CartItem, FavoriteItem


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_brand = serializers.CharField(source="product.brand", read_only=True)
    image_url = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    price_old = serializers.SerializerMethodField()
    size = serializers.CharField(source="size.__str__", read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "product_brand",
            "image_url",
            "price",
            "price_old",
            "size",
            "quantity",
            "subtotal",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.product.image and hasattr(obj.product.image, "url"):
            return request.build_absolute_uri(obj.product.image.url) if request else obj.product.image.url
        return None

    def get_price(self, obj):
        return float(obj.product.discounted_price)

    def get_price_old(self, obj):
        if obj.product.discount:
            return float(obj.product.price)
        return None


class FavoriteItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_brand = serializers.CharField(source="product.brand", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteItem
        fields = ["id", "product_id", "product_name", "product_brand", "image_url", "created_at"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.product.image and hasattr(obj.product.image, "url"):
            return request.build_absolute_uri(obj.product.image.url) if request else obj.product.image.url
        return None