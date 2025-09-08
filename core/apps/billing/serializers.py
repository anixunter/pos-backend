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
    
    class Meta:
        model = ProductReturn
        fields = [
            'id', 'transaction', 'return_date', 
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
        refund_method = data.get('refund_method')
        if refund_method == ProductReturn.RefundMethodChoices.CREDIT:
            transaction = data.get('transaction')
            if transaction and not transaction.customer:
                raise serializers.ValidationError("Credit refunds require a customer to be associated with the original transaction")
        
        #get all products in the current return
        products_id_return = []
        for item in items_data:
            products_id_return.append(item['product'].id)
        
        #get all saled products for this transaction
        sold_items = SalesTransactionItem.objects.filter(
            transaction=transaction,
            product_id__in=products_id_return
        )
        
        #create mapping of product -> quantity sold
        sold_quantities = {}
        for item in sold_items:
            sold_quantities[item.product_id] = item.quantity
            
        #get all previous returns for this transaction
        previous_returns = ProductReturn.objects.filter(transaction=transaction)
        previous_return_items = ProductReturnItem.objects.filter(
            product_return__in=previous_returns,
            product_id__in=products_id_return
        )
        
        #create mapping of product -> quantity returned
        returned_quantities = {}
        for item in previous_return_items:
            returned_quantities[item.product_id] = returned_quantities.get(item.product_id, 0) + item.quantity
        
        #validate each item in the current return
        for item in items_data:
            product_id = item['product'].id
            return_quantity = item['quantity']
            
            #check if product was sold in this transaction
            if product_id not in sold_quantities:
                raise serializers.ValidationError(
                    f"Product {product_id} was not sold in this transaction."
                )
            
            #calculate available return quantity
            sold_quantity = sold_quantities[product_id]
            returned_quantity = returned_quantities.get(product_id, 0)
            available_quantity = sold_quantity - returned_quantity
            
            #validate return quantity
            if return_quantity > available_quantity:
                raise serializers.ValidationError(
                    f"Cannot return {return_quantity} units of product {product_id}. "
                    f"Only {available_quantity} units are returnable."
                )
            
            #validate return quantity is positive
            if return_quantity <= 0:
                raise serializers.ValidationError(
                    f"Return quantity must be greater than 0 for product {product_id}"
                )    
                
        return data


class SalesTransactionSerializer(serializers.ModelSerializer):
    items = SalesTransactionItemSerializer(many=True)
    returns = ProductReturnSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    
    class Meta:
        model = SalesTransaction
        fields = [
            'id', 'customer', 'customer_name', 'transaction_date', 
            'payment_method', 'subtotal', 'discount_amount', 'tax_amount', 
            'total_amount', 'amount_paid', 'change_amount', 'notes', 'items', 'returns'
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
