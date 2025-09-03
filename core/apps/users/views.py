from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.apps.users.models import User, Customer, CustomerDeposit
from core.apps.users.serializers import UserSerializer, CustomerSerializer, CustomerDepositSerializer
from core.apps.users.permissions import IsAdmin, CustomUserPermission

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
        customer = self.get_object()
        transactions = SalesTransaction.objects.filter(customer=customer)
        
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
        if customer.outstandin_balance <= 0:
            return Response(
                {'error':'Customer has no outstanding balance to pay'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount_to_pay = min(payment_amount, customer.outstanding_balance)
            
            customer.outsanding_balance -= amount_to_pay
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
        customer = self.get_object()
        
        balance_info = {
            'outstanding_balance': customer.outstanding_balance,
            'balance_status': 'No balance' if customer.outstanding_balance == 0 else
                            'Credit available' if customer.outstanding_balance < 0 else
                            'Amount owed'
        }
        
        return Response(balance_info)
                
                
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
