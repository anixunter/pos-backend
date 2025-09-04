from django.db import models
from django.core.validators import MinValueValidator
from core.apps.common.models import(
    TimeStampModelMixin,
    AuditModelMixin,
)


class Category(TimeStampModelMixin, AuditModelMixin):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class Supplier(TimeStampModelMixin, AuditModelMixin):
    name = models.CharField(max_length=250)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField()
    
    def __str__(self):
        return self.name


class Product(TimeStampModelMixin, AuditModelMixin):
    class UnitChoices(models.TextChoices):
        PIECE = 'Piece', 'Piece'
        KG = 'Kg', 'Kg'
        SQUARE_METER = 'Sq.m', 'Sq.m'
        
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True)  # Stock Keeping Unit
    barcode = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='products')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    unit_of_measurement = models.CharField(max_length=20, choices=UnitChoices.choices, default=UnitChoices.PIECE)
    
    def __str__(self):
        return self.name


class PurchaseOrder(TimeStampModelMixin, AuditModelMixin):
    class StatusChoices(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        COMPLETED = 'Completed', 'Completed'
    
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    order_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"PO-{self.id} from {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    def __str__(self):
        return f"{self.quantity} of {self.product.name}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price


class ProductPurchasePriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchase_price_history')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateTimeField(auto_now_add=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='price_updates')
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name_plural = 'Product purchase price history'
    
    def __str__(self):
        return f"{self.product.name} - {self.purchase_price} on {self.effective_date.date()}"
    

class InventoryAdjustment(TimeStampModelMixin, AuditModelMixin):
    class AdjustmentTypeChoices(models.TextChoices):
        INCREASE = 'Increase', 'Increase'
        DECREASE = 'Decrease', 'Decrease'
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=10, choices=AdjustmentTypeChoices.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    reason = models.TextField()
    adjustment_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.adjustment_type} {self.quantity} of {self.product.name}"
