from rest_framework import serializers
from core.apps.billing.models import SalesTransactionItem, SalesTransaction, ProductReturnItem, ProductReturn


class SalesTransactionItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = SalesTransactionItem
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_price', 
            'discount_amount', 'total_price'
        ]
    
    def validate(self, data):
        if data.get('discount_amount') and data.get('unit_price') and data.get('quantity'):
            max_discount = data['unit_price'] * data['quantity']
            if data['discount_amount'] > max_discount:
                raise serializers.ValidationError("Discount cannot exceed total item price")
        return data


class SalesTransactionSerializer(serializers.ModelSerializer):
    items = SalesTransactionItemSerializer(many=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    
    class Meta:
        model = SalesTransaction
        fields = [
            'id', 'customer', 'customer_name', 'transaction_date', 'status', 
            'payment_method', 'subtotal', 'discount_amount', 'tax_amount', 
            'total_amount', 'amount_paid', 'change_amount', 'notes', 'items'
        ]
        read_only_fields = [
            'transaction_date', 'status', 
            'subtotal', 'tax_amount', 'total_amount', 'change_amount'
        ]
    
    def validate(self, data):
        # Validate payment for completed transactions
        if data.get('payment_method') == SalesTransaction.PaymentMethodChoices.CASH:
            if not data.get('amount_paid') or data.get('amount_paid', 0) <= 0:
                raise serializers.ValidationError("Amount paid is required for cash payments")
        
        if data.get('payment_method') == SalesTransaction.PaymentMethodChoices.CREDIT:
            if not data.get('customer'):
                raise serializers.ValidationError("Customer is required for credit payments")
        
        return data


class ProductReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ProductReturnItem
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price'
        ]


class ProductReturnSerializer(serializers.ModelSerializer):
    items = ProductReturnItemSerializer(many=True)
    transaction_id = serializers.IntegerField(source='transaction.id', read_only=True)
    
    class Meta:
        model = ProductReturn
        fields = [
            'id', 'transaction', 'transaction_id', 'return_date', 'status', 
            'reason', 'refund_amount', 'notes', 'items'
        ]
        read_only_fields = ['return_date', 'status', 'refund_amount']


