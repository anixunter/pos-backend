from django.core.exceptions import ValidationError
from core.apps.products.models import InventoryAdjustment

def apply_inventory_adjustment(adjustment):
    product = adjustment.product
    quantity = adjustment.quantity
    adjustment_type = adjustment.adjustment_type

    if adjustment_type == InventoryAdjustment.AdjustmentTypeChoices.INCREASE:
        product.current_stock += quantity
    elif adjustment_type == InventoryAdjustment.AdjustmentTypeChoices.DECREASE:
        if product.current_stock < quantity:
            raise ValidationError("Not enough stock for this adjustment")
        product.current_stock -= quantity
    product.save()