import os
import django
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from station.models import Transaction

print("=== DEBUG: Dashboard Query Analysis ===\n")

# Replicate what the dashboard does
today = timezone.localdate()
print(f"Today's date (localdate): {today}")
print(f"Today's date type: {type(today)}")

start_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
end_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

print(f"Start DT: {start_dt}")
print(f"Start DT type: {type(start_dt)}")
print(f"End DT: {end_dt}")
print(f"End DT type: {type(end_dt)}")

print("\n--- Raw Query Test ---")
print(f"Query will be:")
print(f"  created_at__gte={start_dt}")
print(f"  created_at__lte={end_dt}")
print(f"  status='completed'")

print("\n--- All Transactions in Database ---")
all_txns = Transaction.objects.all().order_by('-created_at')
for txn in all_txns:
    print(f"ID: {txn.id}, TX: {txn.transaction_id}")
    print(f"  Created: {txn.created_at} (type: {type(txn.created_at)})")
    print(f"  Timezone info: {txn.created_at.tzinfo}")
    print(f"  Status: {txn.status}")
    print(f"  In range? {start_dt <= txn.created_at <= end_dt}")
    print()

print("\n--- Period Transactions Query ---")
period_transactions = Transaction.objects.filter(
    created_at__gte=start_dt,
    created_at__lte=end_dt,
    status='completed',
)

print(f"Period transactions count: {period_transactions.count()}")
print(f"SQL Query: {period_transactions.query}")

for txn in period_transactions:
    print(f"✓ TX: {txn.transaction_id}, Amount: {txn.total_amount}, Status: {txn.status}")

print("\n--- Dashboard KPI Calculations ---")
today_revenue = period_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
transaction_count = period_transactions.count()
total_fuel_dispensed = period_transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0

print(f"Today's Revenue: GH₵{today_revenue}")
print(f"Transaction Count: {transaction_count}")
print(f"Total Fuel Dispensed: {total_fuel_dispensed}L")

print("\n--- Yesterday Check ---")
yesterday = today - timedelta(days=1)
yesterday_start = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.min.time()))
yesterday_end = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.max.time()))

print(f"Yesterday's date: {yesterday}")
print(f"Yesterday start: {yesterday_start}")
print(f"Yesterday end: {yesterday_end}")

yesterday_transactions = Transaction.objects.filter(
    created_at__gte=yesterday_start,
    created_at__lte=yesterday_end,
    status='completed',
)
print(f"Yesterday transactions count: {yesterday_transactions.count()}")

print("\n=== END DEBUG ===")
