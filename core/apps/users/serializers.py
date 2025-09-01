from rest_framework import serializers
from core.apps.users.models import Customer, CustomerDeposit


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'loyalty_points', 
            'outstanding_balance'
        ]
        read_only_fields = ['loyalty_points']


class CustomerDepositSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)  
    class Meta:
        model = CustomerDeposit
        fields = [
            'id', 'customer', 'customer_name', 'amount', 'deposit_date', 
            'payment_method', 'notes'
        ]
        read_only_fields = ['deposit_date']