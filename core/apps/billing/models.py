from django.db import models
from django.core.validators import MinValueValidator
from core.apps.common.models import (
    TimeStampModelMixin,
    AuditModelMixin,
)
from core.apps.users.models import Customer
from core.apps.products.models import Product


class SalesTransaction(TimeStampModelMixin, AuditModelMixin):
    class PaymentMethodChoices(models.TextChoices):
        CASH = 'Cash', 'Cash'
        ONLINE = 'Online', 'Online'
        CREDIT = 'Credit', 'Credit'
    
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, blank=True, null=True, related_name='sales_transactions')
    transaction_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=10, choices=PaymentMethodChoices.choices)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Sale-{self.id}"


class SalesTransactionItem(models.Model):
    transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.quantity} of {self.product.name}"
    
    @property
    def total_price(self):
        return (self.quantity * self.unit_price) - self.discount_amount
    

# product return models below
class ProductReturn(TimeStampModelMixin, AuditModelMixin):
    class RefundMethodChoices(models.TextChoices):
        CREDIT = 'Credit', 'Credit to Account'
        CASH = 'Cash', 'Cash Refund'
         
    transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='returns')
    return_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_method = models.CharField(max_length=10, choices=RefundMethodChoices.choices, default=RefundMethodChoices.CASH)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Return for Sale-{self.transaction.id}"


class ProductReturnItem(models.Model):
    product_return = models.ForeignKey(ProductReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} of {self.product.name}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
