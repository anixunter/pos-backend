from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action

from core.apps.products.models import Products
from core.apps.billing.models import SalesTransactionItem, SalesTransaction, ProductReturnItem, ProductReturn
from core.apps.billing.serializers import  SalesTransactionSerializer, ProductReturnSerializer
from core.apps.users.permissions import IsAdmin


class SalesTransactionViewSet(viewsets.ModelViewSet):
    queryset = SalesTransaction.objects.select_related('customer').prefetch_related('items__product')
    serializer_class = SalesTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Override to set different permissions for different actions"""
        if self.action == 'update':
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data.pop('items', [])
        
        if not items_data:
            raise serializers.ValidationError("Transaction must have at least one item")
        
        with transaction.atomic():
            #create the main transaction
            sales_transaction = SalesTransaction.objects.create(**serializer.validated_data)
            
            #bulk create items
            if items_data:
                items_to_create = [
                    SalesTransactionItem(transaction=sales_transaction, **item_data)
                    for item_data in items_data
                ]
                SalesTransactionItem.objects.bulk_create(items_to_create)
            
            #caluclate totals
            self._calculate_totals(sales_transaction)
            
            #update inventory
            self._update_inventory(sales_transaction)
            
            #handle customer accounting
            self._handle_customer_accounting(sales_transaction)
        
        return Response(
            self.get_serializer(sales_transaction).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        # For physical store, you might want to disable updates to completed transactions
        # or implement strict rules about what can be modified
        return Response(
            {'error': 'Sales transactions cannot be modified after creation'},
            status=status.HTTP_400_BAD_REQUEST
        )
        
        # ===============
        # If you want update logic later, below are the update logic
        # ===============

        # partial = kwargs.pop('partial', False)
        # instance = self.get_object()
        # serializer = self.get_serializer(instance, data=request.data, partial=partial)
        # serializer.is_valid(raise_exception=True)
        
        # items_data = serializer.validated_data.pop('items', [])
        
        # with transaction.atomic():
        #     #update main fields
        #     super().perform_update(serializer)
            
        #     #handle items with bulk operations
        #     if items_data:
        #         existing_items = {item.id: item for item in instance.items.all()}
                
        #         items_to_keep = set()
        #         items_to_create = []
        #         items_to_update = []
                
        #         for item_data in items_data:
        #             item_id = item_data.get('id')
                    
        #             if item_id and item_id in existing_items:
        #                 #prepare for bulk update
        #                 item = existing_items[item_id]
        #                 for attr, value in item_data.items():
        #                     if attr != 'id':
        #                         setattr(item, attr, value)
        #                 items_to_update.append(item)
        #                 items_to_keep.add(item_id)
        #             else:
        #                 #prepare for bulk create
        #                 items_to_create.append(
        #                     SalesTransactionItem(transaction=instance, **item_data)
        #                 )
                
        #         #bulk operations
        #         if items_to_create:
        #             SalesTransactionItem.objects.bulk_create(items_to_create)
                
        #         if items_to_update:
        #             update_fields = ['product', 'quantity', 'unit_price', 'discount_amount']
        #             SalesTransactionItem.objects.bulk_update(items_to_update, update_fields)
                
        #         #bulk delete items that are no longer needed
        #         items_to_delete = set(existing_items.keys()) - items_to_keep
        #         if itesm_to_delete:
        #             SalesTransactionItem.objects.filter(id__in=items_to_delete).delete()
        #     else:
        #         #if no items data provided, delete all existing items
        #         instance.items.all().delete()
            
        #     #recalculate totals
        #     self._calculate_totals(instance)
        
        # return Response(self.get_serializer(instance).data)
    
    def _calculate_totals(self, instance):
        """Calculate transaction totals and update the instance"""
        #calculate subtotal
        subtotal = sum(item.total_price for item in instance.items.all())
        
        #apply transaction discount
        discount = instance.discount_amount or 0
          
        #calculate total
        total = subtotal - discount
        
        #update instance
        instance.subtotal = subtotal
        instance.total_amount = total
        
        #calculate change if amount paid is provided
        if instance.amount_paid:
            instance.change_amount = max(0, instance.amount_paid - total)
        
        instance.save(update_fields=['subtotal', 'total_amount', 'change_amount'])
    
    def _update_inventory(self, instance):
        """Update product stock levels"""
        items = instance.items.select_related('product').all()
        
        #check stock availability
        for item in items:
            if item.product.current_stock < item.quantity:
                raise serializers.ValidationError(
                    f"Not enough stock for {item.product.name}"
                )
        
        #update inventory
        products_to_update = []
        for item in items:
            product = item.product
            product.current_stock -= item.quantity
            products_to_update.append(product)
        
        Products.objects.bulk_update(products_to_update, ['current_stock'])
    
    def _handle_customer_accounting(self, instance):
        """Handle customer credit/deposit application"""
        if not instance.customer:
            return
        
        customer = instance.customer
        
        #apply existing customer credit (negative balance = credit)
        if customer.outstanding_balance <= 0:
            available_credit = abs(customer.outsanding_balance)
            amount_owed = instance.total_amount - (instance.amount_paid or 0)
            
            if amount_owed > 0:
                credit_to_use = min(available_credit, amount_owed)
                instance.amount_paid = (instance.amount_paid or 0) + credit_to_use
                customer.outstanding_balance += credit_to_use
        
        #handle new credit or partial payments
        current_payment = instance.amount_paid or 0
        amount_owed = instance.total_amount - current_payment
        
        if amount_owed > 0:
                customer.oustanding_balance += amount_owed
        
        customer.save(update_fields=['oustanding_balance'])
        #as amount_paid is modified above internally it need to be updated
        instance.save(update_fields=['amount_paid'])
        

class ProductReturnViewSet(viewsets.ModelViewSet):
    queryset = ProductReturn.objects.select_related('transaction__customer').prefetch_related('items__product')
    serializer_class = ProductReturnSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data.pop('items', [])
        
        with transaction.atomic():
            #create the product return
            product_return = ProductReturn.objects.create(**serializer.validated_data)
            
            #bulk create items
            if items_data:
                items_to_create = [
                    ProductReturnItem(product_return=product_return, **item_data)
                    for item_data in items_data
                ]
                ProductReturnItem.objects.bulk_create(items_to_create)
            
            #calculate refund amount
            self._calculate_refund(product_return)
            
        return Response(
            self.get_serializer(product_return).data,
            status=status.HTTP_201_CREATED
        )
        
    def _calculate_refund(self, instance):
        """Calculate refund amount based on returned items"""
        refund_amount = sum(item.total_price for item in instance.items.all())
        instance.refund_amount = refund_amount
        instance.save(update_fields=[refund_amount])   
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a product return and update inventory"""
        product_return = self.get_object()
        
        if product_return.status != ProductReturn.ReturnStatusChoices.PENDING:
            return Response(
                {'error': 'Only pending returns can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                #bulk update product stock
                items = product_return.items.select_related('prodcut').all()
                products_to_update = []
                
                for item in items:
                    product = item.product
                    product.current_stock += item.quantity
                    products_to_update.append(product)
                
                if products_to_update:
                    Product.objects.bulk_update(products_to_update, ['current_stock'])
                
                #update customer balance if applicable
                if product_return.transaction.customer:
                    customer = product_return.transaction.customer
                    customer.outstanding_balance -= product_return.refund_amount
                    customer.save(update_fields=['outstanding_balance'])
                
                #update return status
                product_return.status = ProductReturn.ReturnStatusChoices.COMPLETED
                product_return.save(update_fields=['status'])
                
                serializer = self.get_serializer(product_return)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
