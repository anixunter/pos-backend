from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from core.apps.products.models import (
    Category, Supplier, Product, PurchaseOrder, PurchaseOrderItem, InventoryAdjustment
)
from core.apps.products.serializers import (
    CategorySerializer, SupplierSerializer, ProductSerializer, PurchaseOrderSerializer, PurchaseOrderItemSerializer, InventoryAdjustmentSerializer
)
from core.apps.products.utils import apply_inventory_adjustment


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


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data.pop('items', [])
        
        with transaction.atomic():
            #create purchase order
            purchase_order = PurchaseOrder.objects.create(**serializer.validated_data)
            
            #bulk create purchase order items
            if items_data:
                items_to_create = [
                    PurchaseOrderItem(purchase_order=purchase_order, **item_data)
                    for item_data in items_data
                ]
                PurchaseOrderItem.objects.bulk_create(items_to_create)
        
        return Response(
            self.get_serializer(purchase_order).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data.pop('items', [])
        
        with transaction.atomic():
            #update main fields
            super().perform_update(serializer)
            
            #handle items with bulk operation
            if items_data:
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
                            #skip the id field and update other item's fields
                            if attr != 'id':
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
            else:
                #if no items data provided, delete all existing items
                instance.items.all().delete()

        return Response(self.get_serializer(instance).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a purchase order and update inventory"""
        purchase_order = self.get_object()
        
        if purchase_order.status != PurchaseOrder.StatusChoices.PENDING:
            return Response(
                {'error': 'Only pending purchase orders can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                #bulk update product stock
                items = purchase_order.items.select_related('product').all()
                products_to_update = []
                
                for item in items:
                    item.product.current_stock += item.quantity
                    products_to_update.append(item.product)
                
                #bulk update products
                if products_to_update:
                    Product.objects.bulk_update(prodcuts_to_update, ['current_stock'])
                
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


class InventoryAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = InventoryAdjustment.objects.select_related('product')
    serializer_class = InventoryAdjustmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        user = self.request.user
        adjustment = serializer.save(created_by=user)

        apply_inventory_adjustment(adjustment)
