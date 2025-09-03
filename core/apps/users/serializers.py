from django.db import transaction
from rest_framework import serializers
from core.apps.users.models import User, Customer, CustomerDeposit


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'password', 'role', 'is_superuser']
        extra_kwargs = {
            "password": {"write_only": True},
            "is_superuser": {"read_only": True}
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        #create user
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        return user
    
    def update(self, instance, validated_data):
        #handle password update separately
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        
        #update remaining fields
        return super().update(instance, validated_data)      


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
            'id', 'customer', 'customer_name', 'amount', 'deposit_date', 'notes'
        ]
        read_only_fields = ['deposit_date']