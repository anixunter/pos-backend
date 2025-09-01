from django.db import models
from django.contrib.auth.models import AbstractUser
from core.apps.common.models import (
    TimeStampModelMixin,
    AuditModelMixin,
    SoftDeleteModelMixin,
    UserManager,
)
from core.apps.billing.models import SalesTransaction

class User(SoftDeleteModelMixin, TimeStampModelMixin, AuditModelMixin, AbstractUser):
    class RoleChoices(models.TextChoices):
        ADMIN = 'Admin', 'Admin'
        STAFF = 'Staff', 'Staff'
        
    role = models.CharField(choices=RoleChoices.choices, default=RoleChoices.STAFF)

    objects = UserManager()

    class Meta:
        db_table = "auth_user"

    def __str__(self):
        return self.username


class Customer(TimeStampModelMixin, AuditModelMixin):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    outstanding_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return self.name


class CustomerDeposit(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='deposits')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=10, choices=SalesTransaction.PaymentMethodChoices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Deposit of {self.amount} by {self.customer.name}"
