from rest_framework import serializers
from .models import PaymentProvider, PaymentGatewayLog, CardToken
from station.models import Transaction


class PaymentProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProvider
        fields = ['id', 'name', 'is_active', 'transaction_fee_percentage']
        read_only_fields = ['name']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for station.models.Transaction (sales transactions)"""
    pump_number = serializers.CharField(source='pump.pump_number', read_only=True)
    fuel_type_name = serializers.CharField(source='fuel_type.name', read_only=True)
    customer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_id', 'pump_number', 'fuel_type_name', 'liters_dispensed',
                  'price_per_liter', 'total_amount', 'payment_method', 'status',
                  'reference_number', 'customer_name', 'created_at', 'completed_at']
        read_only_fields = ['created_at', 'completed_at', 'transaction_id']
    
    def get_customer_name(self, obj):
        if obj.customer:
            return f"{obj.customer.first_name} {obj.customer.last_name}"
        return None


class PaymentGatewayLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGatewayLog
        fields = ['id', 'transaction', 'provider', 'request_data',
                  'response_data', 'status_code', 'error_message', 'reference', 'created_at']
        read_only_fields = ['created_at']


class CardTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardToken
        fields = ['id', 'phone', 'card_token', 'card_last4', 'card_type', 'is_primary', 'expires_at']
        read_only_fields = ['card_token']
