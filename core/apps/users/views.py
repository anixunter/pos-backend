from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.apps.users.models import Customer
from core.apps.users.serializers import CustomerSerializer


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
    
    @action(detail=True, methods=['post'])
    def add_deposit(self, request, pk=None):
        """Add a deposit for a customer"""
        customer = self.get_object()
        serializer = CustomerDepositSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(customer=customer)
            return Response({
                'message': 'Deposit added successfully',
                'new_balance': customer.outstanding_balance,
                'deposit_id': serializer.data['id']
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
