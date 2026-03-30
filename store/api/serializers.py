from rest_framework import serializers

from ..models import CartItem, FavoriteItem, Product


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


class BulkProductCommonSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    brand = serializers.CharField(max_length=100, allow_blank=True, required=False)
    category_id = serializers.IntegerField(required=False, allow_null=True)  # accept category id (form uses 'category')
    season = serializers.CharField(max_length=50, allow_blank=True, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    discount = serializers.IntegerField(min_value=0, max_value=100, required=False)
    is_active = serializers.BooleanField(required=False, default=True)
    status = serializers.ChoiceField(choices=Product.Status.choices, required=False, default=Product.Status.AVAILABLE)
    sizes = serializers.ListField(child=serializers.IntegerField(), required=False)