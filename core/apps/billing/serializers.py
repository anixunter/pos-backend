from rest_framework import serializers
from core.apps.billing.models import SalesTransactionItem, SalesTransaction, CustomerDeposit, ProductReturnItem, ProductReturn


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
    change_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
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
    
    # def create(self, validated_data):
    #     items_data = validated_data.pop('items')
    #     sales_transaction = SalesTransaction.objects.create(**validated_data)
        
    #     for item_data in items_data:
    #         SalesTransactionItem.objects.create(transaction=sales_transaction, **item_data)
        
    #     # Calculate totals
    #     self._calculate_totals(sales_transaction)
        
    #     return sales_transaction
    
    # def update(self, instance, validated_data):
    #     items_data = validated_data.pop('items', None)
        
    #     # Update transaction fields
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()
        
    #     # Update items if provided
    #     if items_data is not None:
    #         # Delete existing items not in the update
    #         existing_items = {item.id: item for item in instance.items.all()}
    #         new_item_ids = []
            
    #         for item_data in items_data:
    #             item_id = item_data.get('id')
    #             if item_id and item_id in existing_items:
    #                 # Update existing item
    #                 item = existing_items.pop(item_id)
    #                 for attr, value in item_data.items():
    #                     setattr(item, attr, value)
    #                 item.save()
    #                 new_item_ids.append(item_id)
    #             else:
    #                 # Create new item
    #                 new_item = SalesTransactionItem.objects.create(transaction=instance, **item_data)
    #                 new_item_ids.append(new_item.id)
            
    #         # Delete items not in the update
    #         for item in existing_items.values():
    #             item.delete()
        
    #     # Recalculate totals
    #     self._calculate_totals(instance)
        
    #     return instance
    
    # def _calculate_totals(self, instance):
    #     # Calculate subtotal
    #     subtotal = sum(item.total_price for item in instance.items.all())
        
    #     # Apply transaction discount
    #     discount = instance.discount_amount or 0
        
    #     # Calculate tax (simplified - in real system you'd have tax rules)
    #     tax_rate = 0.1  # 10% tax
    #     tax_amount = (subtotal - discount) * tax_rate
        
    #     # Calculate total
    #     total = subtotal - discount + tax_amount
        
    #     # Update instance
    #     instance.subtotal = subtotal
    #     instance.tax_amount = tax_amount
    #     instance.total_amount = total
        
    #     # Calculate change if amount paid is provided
    #     if instance.amount_paid:
    #         instance.change_amount = max(0, instance.amount_paid - total)
        
    #     instance.save()


class CustomerDepositSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = CustomerDeposit
        fields = [
            'id', 'customer', 'customer_name', 'amount', 'deposit_date', 
            'payment_method', 'notes'
        ]
        read_only_fields = ['deposit_date']


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
    
    # def create(self, validated_data):
    #     items_data = validated_data.pop('items')
    #     product_return = ProductReturn.objects.create(**validated_data)
        
    #     for item_data in items_data:
    #         ProductReturnItem.objects.create(product_return=product_return, **item_data)
        
    #     # Calculate refund amount
    #     self._calculate_refund(product_return)
        
    #     return product_return
    
    # def _calculate_refund(self, instance):
    #     # Calculate refund amount based on returned items
    #     refund_amount = sum(item.total_price for item in instance.items.all())
    #     instance.refund_amount = refund_amount
    #     instance.save()


