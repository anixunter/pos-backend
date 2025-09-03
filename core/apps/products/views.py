from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from core.apps.products.models import (
    Category, Supplier, Product, PurchaseOrder, PurchaseOrderItem, InventoryAdjustment, ProductPurchasePriceHistory
)
from core.apps.products.serializers import (
    CategorySerializer, SupplierSerializer, ProductSerializer, PurchaseOrderSerializer, InventoryAdjustmentSerializer, ProductPurchasePriceHistorySerializer
)
from core.apps.products.utils import apply_inventory_adjustment
from core.apps.users.permissions import IsSuperUser, IsAdmin, IsStaff


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'supplier')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Override to set different permissions for different actions"""
        if self.action == 'adjust_stock':
            self.permission_classes = [IsSuperUser | IsAdmin]
        return [permission() for permission in self.permission_classes]
        
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def adjust_stock(self, request, pk=None):
        """Custom action to adjust product stock"""
        product = self.get_object()
        serializer = InventoryAdjustmentSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            adjustment = serializer.save(product=product, created_by=request.user)
            apply_inventory_adjustment(adjustment)
            return Response({
                'message': 'Stock adjusted successfully',
                'adjusted_stock': product.current_stock,
                'adjustment_id': adjustment.id
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock"""
        low_stock_products = self.get_queryset().filter(
            current_stock__lte=F('minimum_stock')
        )
        serializer = self.get_serializer(low_stock_products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        product = self.get_object()
        limit = int(request.query_params.get('limit', 5))
        
        price_history = product.purchase_price_history.all()[:limit]
        serializer = ProductPurchasePriceHistorySerializer(price_history, many=True)
        
        return Response(
            {
                'product_id': product.id,
                'product_name': product.name,
                'current_purchase_price': product.purchase_price,
                'price_history': serializer.data
            }
        )


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsSuperUser | IsAdmin]
    
    def create(self, request, *args, **kwargs):
        """Create a draft (PENDING) purchase order"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data.pop('items', [])
        
        with transaction.atomic():
            #create purchase order as draft/pending by default
            purchase_order = PurchaseOrder.objects.create(**serializer.validated_data)
            
            #bulk create purchase order items
            if items_data:
                items_to_create = [
                    PurchaseOrderItem(purchase_order=purchase_order, **item_data)
                    for item_data in items_data
                ]
                PurchaseOrderItem.objects.bulk_create(items_to_create)
            
            #calculate total amount
            self._calculate_total(purchase_order)
        
        return Response(
            self.get_serializer(purchase_order).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update purchase order - only allowed for PENDING status"""
        instance = self.get_object()
        
        #prevent updates to completed orders
        if instance.status != PurchaseOrder.StatusChoices.PENDING:
            return Response(
                {'error':'Cannot modify completed purchase orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data.pop('items', None) # use none to distinguish from empty list
        
        with transaction.atomic():
            #update main fields
            super().perform_update(serializer)
            
            #handle items with bulk operation
            if items_data is not None:
                existing_items = {item.id: item for item in instance.items.all()}
                items_to_keep = set()
                items_to_create = []
                items_to_update = []

                for item_data in items_data:
                    item_id = item_data.get('id')
                    if item_id and item_id in existing_items:
                        #prepare for bulk update
                        item = existing_items[item_id]
                        for attr, val in item_data.items():
                            #skip the id and received_quantity field and update other item's fields
                            if attr != 'id' and attr != 'received_quantity':
                                setattr(item, attr, val)
                        items_to_update.append(item)
                        items_to_keep.add(item_id)
                    else:
                        #prepare for bulk create
                        items_to_create.append(
                            PurchaseOrderItem(purchase_order=instance, **item_data)
                        )
                
                #bulk operations
                if items_to_create:
                    PurchaseOrderItem.objects.bulk_create(items_to_create)
                
                if items_to_update:
                    update_fields = ['product', 'quantity', 'unit_price']
                    PurchaseOrderItem.objects.bulk_update(items_to_update, update_fields)

                #bulk delete items that are no longer needed
                items_to_delete = set(existing_items.keys()) - items_to_keep
                if items_to_delete:
                    PurchaseOrderItem.objects.filter(id__in=items_to_delete).delete()
            
            #recalculate total
            self._calculate_total(instance)

        return Response(self.get_serializer(instance).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a purchase order and update inventory based on received quantities"""
        purchase_order = self.get_object()
        
        if purchase_order.status != PurchaseOrder.StatusChoices.PENDING:
            return Response(
                {'error': 'Only pending purchase orders can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        received_quantities = request.data.get('received_quantities', {})
        #------------------------------#
        # sample payload from frontend #
        #------------------------------#
        # {
        #     "received_quantities": {
        #         "1": 5,    # Item ID 1, received 5 units
        #         "2": 3     # Item ID 2, received 3 units
        #     }
        # }
        
        try:
            with transaction.atomic():
                #update received quantities if provided
                if received_quantities:
                    for item_id, received_qty in received_quantities.items():
                        try:
                            item = purchase_order.items.get(id=item.id)
                            if received_qty > item.quantity:
                                raise ValidationError(
                                    "Received quantity exceeded ordered quantity"
                                )
                            item.received_quantity = received_qty
                            item.save(update_fields=['received_quantity'])
                        except PurchaseOrderItem.DoesNotExist:
                            raise ValidationError(f"Item with id {item_id} not found in this purchase order")
                
                #update inventory and track purchase prices
                self._update_inventory_and_prices(purchase_order)
                
                #update purchase order status
                purchase_order.status = PurchaseOrder.StatusChoices.COMPLETED
                purchase_order.save(update_fields=['status'])
                
                serializer = self.get_serializer(purchase_order)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _update_inventory_and_prices(self, instance):
        """Update inventory and track purchase prices in history"""
        items = instance.items.select_related('product').all()
        products_to_update = []
        price_history_to_create = []
        
        for item in items:
            quantity_to_add = item.received_quantity
            #skip items with zero received quantity
            if quantity_to_add == 0:
                continue
            
            product = item.product
            
            #update product stock
            product.current_stock += quantity_to_add
            
            #check if purchase price has changed before updating and creating history
            price_has_changed = product.purchase_price != item.unit_price
            
            if price_has_changed:
            # update the current purchase price only if it changed
                product.purchase_price = item.unit_price
            
                #create price history record only if price changed
                price_history_to_create.append(
                    ProductPurchasePriceHistory(
                        product=product,
                        purchase_price=item.unit_price,
                        purchase_order=instance,
                        quantity_received=quantity_to_add
                    )
                )
            
            #create update product record
            products_to_update.append(product)
        
        #bulk update products
        if products_to_update:
            update_fields = ['current_stock']
            if price_history_to_create:
                update_fields.append('purchase_price')
            Product.objects.bulk_update(products_to_update, update_fields)
        
        #bulk create price history records
        if price_history_to_create:
            ProductPurchasePriceHistory.objects.bulk_create(price_history_to_create)


class InventoryAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = InventoryAdjustment.objects.select_related('product')
    serializer_class = InventoryAdjustmentSerializer
    permission_classes = [IsSuperUser | IsAdmin]
    
    def perform_create(self, serializer):
        user = self.request.user
        adjustment = serializer.save(created_by=user)

        apply_inventory_adjustment(adjustment)
