import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from transactions.models import Pump, Transaction
from django.db.models import Sum

print('--- (1) Pumps Information ---')
try:
    pumps = Pump.objects.all()
    for p in pumps:
        print(f'ID: {p.id}, Pump Number: {p.pump_number}, Fuel Type: {p.fuel_type}, Status: {p.status}, Total Liters: {p.total_liters_dispensed}, Total Revenue: {p.total_revenue}')
except Exception as e: print(f'Error Pumps: {e}')

print('\n--- (2) Completed Transactions Grouped by Pump ---')
try:
    stats = Transaction.objects.filter(status='completed').values('pump_id').annotate(
        total_liters=Sum('liters_dispensed'),
        total_amount=Sum('total_price')
    ).order_by('pump_id')
    for s in stats:
        print(f"Pump ID: {s['pump_id']}, Sum Liters: {s['total_liters']}, Sum Amount: {s['total_amount']}")
except Exception as e: print(f'Error Grouped: {e}')

print('\n--- (3) Top 10 Oldest Completed Transactions ---')
try:
    oldest = Transaction.objects.filter(status='completed').order_by('created_at')[:10]
    for t in oldest:
        print(f'Pump ID: {t.pump_id}, Liters: {t.liters_dispensed}, Amount: {t.total_price}, Payment: {t.payment_method}, Trans ID: {t.id}, Ref: {t.reference_number}, Created: {t.created_at}')
except Exception as e: print(f'Error Transactions: {e}')
