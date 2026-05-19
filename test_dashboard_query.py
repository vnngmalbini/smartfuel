import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from station.models import Transaction
from django.db.models import Sum

# Replicate the dashboard query
today = timezone.localdate()
print(f'Today (local): {today}')

start_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
end_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

print(f'Start DT: {start_dt}')
print(f'End DT: {end_dt}')

period_transactions = Transaction.objects.filter(
    created_at__gte=start_dt,
    created_at__lte=end_dt,
    status='completed',
)

print(f'\nTransactions found: {period_transactions.count()}')
print(f'Query: {period_transactions.query}')

for txn in period_transactions:
    print(f'  ID: {txn.id}, TX: {txn.transaction_id}, Status: {txn.status}, Amount: {txn.total_amount}, Created: {txn.created_at}')

today_revenue = period_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
transaction_count = period_transactions.count()
total_fuel_dispensed = period_transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0

print(f'\nToday revenue: {today_revenue}')
print(f'Transaction count: {transaction_count}')
print(f'Total fuel dispensed: {total_fuel_dispensed}')
