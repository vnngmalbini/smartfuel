from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Sum, Count

from .models import PaymentProvider, PaymentGatewayLog, CardToken
from station.models import Transaction
from .serializers import (
    PaymentProviderSerializer, PaymentTransactionSerializer,
    PaymentGatewayLogSerializer, CardTokenSerializer
)


class PaymentProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for payment providers"""
    queryset = PaymentProvider.objects.filter(is_active=True)
    serializer_class = PaymentProviderSerializer
    permission_classes = [IsAuthenticated]


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for payment transactions (from station.models.Transaction)"""
    queryset = Transaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method']
    search_fields = ['transaction_id', 'reference_number']
    ordering_fields = ['created_at', 'total_amount']
    
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Get today's payment summary"""
        today = timezone.now().date()
        today_transactions = Transaction.objects.filter(
            created_at__date=today,
            status='completed'
        ).exclude(fuel_type__name__iexact='lpg')
        
        summary = {
            'total_transactions': today_transactions.count(),
            'total_amount': today_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'total_liters': today_transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0,
            'by_method': {}
        }
        
        # Group by payment method
        method_summary = today_transactions.values('payment_method').annotate(
            count=Count('id'),
            amount=Sum('total_amount')
        )
        
        for item in method_summary:
            method = item['payment_method'] or 'unknown'
            summary['by_method'][method] = {
                'count': item['count'],
                'amount': float(item['amount'] or 0)
            }
        
        return Response(summary)


class PaymentGatewayLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for payment gateway logs"""
    queryset = PaymentGatewayLog.objects.all()
    serializer_class = PaymentGatewayLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['provider', 'transaction']
    ordering_fields = ['-created_at']


class CardTokenViewSet(viewsets.ModelViewSet):
    """API endpoints for saved card tokens"""
    serializer_class = CardTokenSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['-created_at']
    
    def get_queryset(self):
        """Return only user's own saved cards"""
        user = self.request.user
        return CardToken.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set a card as primary"""
        card = self.get_object()
        
        # Remove primary from all other cards
        CardToken.objects.filter(user=request.user).update(is_primary=False)
        
        # Set this as primary
        card.is_primary = True
        card.save()
        
        return Response(CardTokenSerializer(card).data)
