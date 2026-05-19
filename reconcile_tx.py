from django.utils import timezone
from station.models import Transaction, Payment
from django.db import transaction as db_transaction

# Find Transaction id=11
try:
    tx = Transaction.objects.get(id=11)
    
    # Create or update Payment
    payment, created = Payment.objects.update_or_create(
        transaction=tx,
        defaults={
            'amount': tx.total_amount,
            'payment_method': 'paystack',
            'reference': tx.reference_number,
            'status': 'completed',
            'provider_response': {'source': 'manual-reconcile'}
        }
    )
    print(f"Payment {'created' if created else 'updated'} for Transaction 11.")
except Transaction.DoesNotExist:
    print("Transaction 11 not found.")

# Today's completed transactions
today = timezone.now().date()
today_tx_ids = list(Transaction.objects.filter(
    status='completed', 
    created_at__date=today
).values_list('id', flat=True))

# Today's payments (transaction IDs)
today_p_tx_ids = list(Payment.objects.filter(
    status='completed',
    created_at__date=today
).values_list('transaction_id', flat=True))

print(f"Today's completed transaction IDs: {today_tx_ids}")
print(f"Today's payment transaction IDs: {today_p_tx_ids}")
