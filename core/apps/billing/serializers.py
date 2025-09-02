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
            'id', 'customer', 'customer_name', 'transaction_date', 
            'payment_method', 'subtotal', 'discount_amount', 'tax_amount', 
            'total_amount', 'amount_paid', 'change_amount', 'notes', 'items'
        ]
        read_only_fields = [
            'transaction_date', 'subtotal', 'tax_amount',
            'total_amount', 'change_amount'
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
            'id', 'transaction', 'transaction_id', 'return_date', 
            'reason', 'refund_amount', 'refund_method', 'notes', 'items'
        ]
        read_only_fields = ['return_date', 'refund_amount']
    
    def validate(self, data):
        transaction = data.get('transaction')
        items_data = data.get('items', [])
        
        # Validate that return has at least one item
        if not items_data:
            raise serializers.ValidationError("Return must have at least one item")
        
        # Validate that credit refunds require a customer
        refund_method = data.get('refund_method', ProductReturn.RefundMethodChoices.CREDIT)
        if refund_method == ProductReturn.RefundMethodChoices.CREDIT:
            transaction = data.get('transaction')
            if transaction and not transaction.customer:
                raise serializers.ValidationError("Credit refunds require a customer to be associated with the original transaction")
        
        return data


