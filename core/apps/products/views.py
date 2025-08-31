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
    def adjust_stock(self, request, pk=None):
        """Custom action to adjust product stock"""
        product = self.get_object()
        serializer = InventoryAdjustmentSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            adjustment = serializer.save(product=product)
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
            purchase_order = PurchaseOrder.objects.create(**serializer.validated_data)
            for item_data in items_data:
                PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)
        
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
            # for attr, value in serializer.validated_data.items():
            #     setattr(instance, attr, value)
            # instance.save()
            instance = super().update(instance, serializer.validated_data)
            
            existing_items = {item.id: item for item in instance.items.all()}
            updated_item_ids = []

            for item_data in items_data:
                item_id = item_data.get('id')
                if item_id and item_id in existing_items:
                    item = existing_items.pop(item_id)
                    for attr, val in item_data.items():
                        setattr(item, attr, val)
                    item.save()
                    updated_item_ids.append(item_id)
                else:
                    new_item = PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
                    updated_item_ids.append(new_item.id)

            # Delete removed items
            for item in existing_items.values():
                item.delete()

        return Response(self.get_serializer(instance).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a purchase order and update inventory"""
        purchase_order = self.get_object()
        
        if purchase_order.status != 'Pending':
            return Response(
                {'error': 'Only pending purchase orders can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Update product stock
                for item in purchase_order.items.all():
                    product = item.product
                    product.current_stock += item.quantity
                    product.save()
                
                # Update purchase order status
                purchase_order.status = 'Completed'
                purchase_order.save()
                
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

        product = adjustment.product
        if adjustment.adjustment_type == 'Increase':
            product.current_stock += adjustment.quantity
        elif adjustment.adjustment_type == 'Decrease':
            if product.current_stock < adjustment.quantity:
                raise serializers.ValidationError("Not enough stock for this adjustment")
            product.current_stock -= adjustment.quantity
        product.save()
