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


class SMSDeliveryLog(models.Model):
    """Track SMS delivery lifecycle for payments and admin test messages."""

    PURPOSE_CHOICES = [
        ('payment_confirmation', 'Payment Confirmation'),
        ('test_sms', 'Test SMS'),
        ('receipt_sms', 'Receipt SMS'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('retrying', 'Retrying'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    transaction = models.ForeignKey(StationTransaction, on_delete=models.CASCADE, related_name='sms_delivery_logs', null=True, blank=True)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES, default='payment_confirmation')
    provider = models.CharField(max_length=50)
    recipient_phone = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=200, blank=True, default='')
    customer_email = models.EmailField(blank=True, default='')
    reference = models.CharField(max_length=100, db_index=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    provider_message_id = models.CharField(max_length=120, blank=True)
    provider_response = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['reference', 'purpose'], name='uniq_sms_delivery_reference_purpose'),
        ]

    def __str__(self):
        return f"SMS {self.purpose} - {self.reference} - {self.status}"


class PaymentAuditLog(models.Model):
    """Event log for payment, SMS, retry, and admin actions."""

    EVENT_CHOICES = [
        ('payment_verified', 'Payment Verified'),
        ('payment_saved', 'Payment Saved'),
        ('sms_queued', 'SMS Queued'),
        ('sms_sent', 'SMS Sent'),
        ('sms_failed', 'SMS Failed'),
        ('sms_retry', 'SMS Retry Scheduled'),
        ('sms_skipped', 'SMS Skipped'),
        ('admin_action', 'Admin Action'),
        ('webhook_verified', 'Webhook Verified'),
        ('webhook_rejected', 'Webhook Rejected'),
    ]

    transaction = models.ForeignKey(StationTransaction, on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    payment = models.ForeignKey('station.Payment', on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    reference = models.CharField(max_length=100, blank=True, default='')
    message = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.reference or self.id}"


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