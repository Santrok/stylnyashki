"""DRF serializers for store models."""

from rest_framework import serializers
from .models import Product, SizeOption, Cart, CartItem


class SizeOptionSerializer(serializers.ModelSerializer):
    """Serializer for clothing size options."""

    class Meta:
        model = SizeOption
        fields = ['id', 'value']


class ProductSerializer(serializers.ModelSerializer):
    """Full serializer for Product including sizes and computed discounted price."""

    sizes = SizeOptionSerializer(many=True, read_only=True)
    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'category', 'season',
            'price', 'discount', 'discounted_price',
            'is_active', 'created_at', 'sizes', 'image',
        ]


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listings."""

    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'brand', 'category', 'price', 'discount', 'discounted_price', 'image']


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for a single cart line item."""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        source='product',
        write_only=True,
    )
    size = SizeOptionSerializer(read_only=True)
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=SizeOption.objects.all(),
        source='size',
        write_only=True,
        required=False,
        allow_null=True,
    )
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'size', 'size_id', 'quantity', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for the shopping cart including all line items and total."""

    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'created_at']
