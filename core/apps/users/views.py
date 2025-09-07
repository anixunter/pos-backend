from django.db import transaction
from django.http import Http404
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.apps.users.models import User, Customer, CustomerDeposit
from core.apps.users.serializers import UserSerializer, CustomerSerializer, CustomerDepositSerializer
from core.apps.billing.models import SalesTransaction, ProductReturn
from core.apps.billing.serializers import SalesTransactionSerializer, ProductReturnSerializer
from core.apps.users.permissions import CustomUserPermission

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [CustomUserPermission]
        
    @action(detail=False, methods=['get'], url_path='self')
    def self_detail(self, request):
        """
        Get the current user's details.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def purchase_history(self, request, pk=None):
        """Get customer purchase history"""
        try:
            customer = self.get_object()
        except Http404:
            return Response(
                {"error": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        transactions = SalesTransaction.objects.filter(customer=customer)
        if not transactions.exists():
            return Response(
                {"message": "No purchase history found for this customer."},
                status=status.HTTP_200_OK
            )
        
        serializer = SalesTransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pay_credit(self, request, pk=None):
        """Allow customer to pay off their outstanding balance"""
        customer = self.get_object()
        payment_amount = request.data.get('payment_amount', 0)
        
        if payment_amount <= 0:
            return Response(
                {'error': 'Payment amount must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )

        #customer owes money (positive oustanding balance ) or has credit (negative outstanding balance)
        #we only allow paying off debt, not adding to credit
        if customer.outstanding_balance <= 0:
            return Response(
                {'error':'Customer has no outstanding balance to pay'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount_to_pay = min(payment_amount, customer.outstanding_balance)
            
            customer.outstanding_balance -= amount_to_pay
            customer.save(update_fields=['outstanding_balance'])
            
            return Response({
                'message': f'Successfully paid ${amount_to_pay}',
                'remaining_balance': customer.outstanding_balance,
                'payment_amount': amount_to_pay},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def balance_summary(self, request, pk=None):
        """Get customer balance summary"""
        try:
            customer = self.get_object()
        except Http404:
            return Response(
                {'error':'Customer not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        balance_info = {
            'outstanding_balance': customer.outstanding_balance,
            'balance_status': 'No balance' if customer.outstanding_balance == 0 else
                            'Credit available' if customer.outstanding_balance < 0 else
                            'Amount owed'
        }
        
        return Response(balance_info)
    
    @action(detail=True, methods=['get'])
    def return_history(self, request, pk=None):
        """Get customer purchase history"""
        try:
            customer = self.get_object()
        except Http404:
            return Response(
                {"error": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        returns = ProductReturn.objects.select_related('transaction__customer').filter(transaction__customer=customer)
        if not returns.exists():
            return Response(
                {"message": "No return history found for this customer."},
                status=status.HTTP_200_OK
            )
        
        serializer = ProductReturnSerializer(returns, many=True)
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
        
        return Response(
            self.get_serializer(deposit).data,
            status=status.HTTP_201_CREATED
        )
