from django.db import models
from django.contrib.auth.models import User
from station.models import Transaction as StationTransaction

class PaymentProvider(models.Model):
    """Payment providers: Paystack, Mobile Money, Card networks"""
    PROVIDER_CHOICES = [
        ('paystack', 'Paystack'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('bank_card', 'Bank Card'),
    ]
    
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    transaction_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.50)
    
    def __str__(self):
        return self.get_name_display()


class PaymentGatewayLog(models.Model):
    """Log all payment gateway API calls"""
    # Reference station.Transaction instead of the deleted payment.Transaction
    transaction = models.ForeignKey(StationTransaction, on_delete=models.CASCADE, related_name='payment_gateway_logs', null=True, blank=True)
    provider = models.ForeignKey(PaymentProvider, on_delete=models.PROTECT)
    request_data = models.JSONField()
    response_data = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True, help_text="Paystack transaction reference")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"PayGW Log - {self.reference or self.id}"


class CardToken(models.Model):
    """Saved card tokens for recurring payments"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_cards', null=True, blank=True)
    phone = models.CharField(max_length=20)
    card_token = models.CharField(max_length=255)
    card_last4 = models.CharField(max_length=4)
    card_type = models.CharField(max_length=50)  # Visa, Mastercard, etc.
    is_primary = models.BooleanField(default=False)
    expires_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"{self.card_type} ****{self.card_last4}"