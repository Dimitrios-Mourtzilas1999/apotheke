from rest_framework import serializers
from .models import Product, Category, Supplier


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    total_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'cat_type', 'product_count', 'total_stock']


class SupplierSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'phone', 'email', 'product_count']


class ProductSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='desc', read_only=True)
    category = serializers.CharField(source='category.cat_type', read_only=True, allow_null=True)
    supplier = serializers.CharField(source='supplier.name', read_only=True, allow_null=True)
    image = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'barcode', 'description', 'category', 'supplier',
            'stock', 'price', 'image', 'qr_code'
        ]

    def get_image(self, obj):
        if obj.image:
            return obj.image_url
        return None

    def get_qr_code(self, obj):
        if obj.qr_code:
            return f"/media/qrcodes/{obj.qr_code}"
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='desc', read_only=True)
    category = serializers.CharField(source='category.cat_type', read_only=True, allow_null=True)
    supplier = serializers.CharField(source='supplier.name', read_only=True, allow_null=True)
    image = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()
    date_added = serializers.DateTimeField(source='date_created', read_only=True)
    date_updated = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'barcode', 'description', 'category', 'supplier',
            'stock', 'price', 'image', 'qr_code',
            'date_added', 'date_updated'
        ]

    def get_image(self, obj):
        if obj.image:
            return obj.image_url
        return None

    def get_qr_code(self, obj):
        if obj.qr_code:
            return f"/media/qrcodes/{obj.qr_code}"
        return None


class CategoryProductSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='desc', read_only=True)
    supplier = serializers.CharField(source='supplier.name', read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = ['id', 'barcode', 'description', 'supplier', 'stock', 'price']


class SupplierProductSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='desc', read_only=True)
    category = serializers.CharField(source='category.cat_type', read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = ['id', 'barcode', 'description', 'category', 'stock', 'price']


class LowStockProductSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='desc', read_only=True)
    category = serializers.CharField(source='category.cat_type', read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = ['id', 'barcode', 'description', 'category', 'stock']
