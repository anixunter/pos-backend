from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.apps.users.models import Customer, CustomerDeposit
from core.apps.users.serializers import CustomerSerializer, CustomerDepositSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def purchase_history(self, request, pk=None):
        """Get customer purchase history"""
        customer = self.get_object()
        transactions = SalesTransaction.objects.filter(customer=customer, status='completed')
        
        serializer = SalesTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class CustomerDepositViewSet(viewsets.ModelViewSet):
    queryset = CustomerDeposit.objects.select_related('customer')
    serializer_class = CustomerDepositSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            #create the deposit
            deposit = CustomerDeposit.objects.create(**serializer.validated_data)
            
            #update customer balance
            customer = deposit.customer
            customer.outstanding_balance -= deposit.amount
            customer.save(update_fields=['outstanding_balance'])
        
        return Respone(
            self.get_serializer(deposit).data,
            status=status.HTTP_201_CREATED
        )
