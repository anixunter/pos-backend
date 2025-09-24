from rest_framework import serializers
from core.apps.products.models import (
    Category, Supplier, Product, PurchaseOrder, PurchaseOrderItem,
    InventoryAdjustment, ProductPurchasePriceHistory
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'address']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'sku', 'barcode', 'category', 'category_name',
            'supplier', 'supplier_name', 'purchase_price', 'selling_price', 'current_stock',
            'minimum_stock', 'unit_of_measurement'
        ]
    
    def validate(self, data):
        if data.get('selling_price') and data.get('purchase_price'):
            if data['selling_price'] < data['purchase_price']:
                raise serializers.ValidationError("Selling price cannot be less than purchase price")
        return data


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) 
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_price', 
            'received_quantity', 'total_price'
        ]
        read_only_fields = ['received_quantity']  # Initially read-only, updated during completion


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True) 
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'supplier', 'supplier_name', 'order_date', 'status', 
            'total_amount', 'notes', 'items'
        ]
        read_only_fields = ['order_date', 'status', 'total_amount']


class ProductPurchasePriceHistorySerializer(serializers.ModelSerializer):
    purchase_order_reference = serializers.CharField(source='purchase_order.__srt__', read_only=True)
    class Meta:
        model = ProductPurchasePriceHistory
        fields = [
            'purchase_price', 'effective_date', 'purchase_order',
            'purchase_order_reference', 'quantity_received'
        ]


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    adjusted_by = serializers.CharField(source='created_by.username', read_only=True)
    class Meta:
        model = InventoryAdjustment
        fields = ['id', 'product', 'product_name', 'adjustment_type', 'quantity', 
            'reason', 'adjustment_date', 'adjusted_by']


class AdjustStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryAdjustment
        fields = ['adjustment_type', 'quantity', 'reason']
    
