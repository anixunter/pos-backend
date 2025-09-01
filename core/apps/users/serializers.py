from rest_framework import serializers
from core.apps.users.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'loyalty_points', 
            'outstanding_balance'
        ]
        read_only_fields = ['loyalty_points']