#!/usr/bin/env python
"""Diagnostic script to investigate revenue dashboard issue"""

import os
import django
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.db.models import Sum
from station.models import Transaction, FuelType

print("=" * 70)
print("REVENUE DASHBOARD DIAGNOSTIC")
print("=" * 70)

# Check current time
now = timezone.now()
today = timezone.localdate()
print(f"\nCurrent server time: {now}")
print(f"Current server date: {today}")
print(f"Timezone: {timezone.get_current_timezone()}")

# Check total transactions
total_txns = Transaction.objects.count()
print(f"\n📊 Total transactions in database: {total_txns}")

# Check transactions by status
print("\n📋 Transactions by status:")
for status in ['pending', 'completed', 'failed', 'refunded']:
    count = Transaction.objects.filter(status=status).count()
    print(f"  - {status}: {count}")

# Check today's transactions
print(f"\n📅 Today's transactions (date={today}):")
today_all = Transaction.objects.filter(created_at__date=today)
print(f"  - Total today: {today_all.count()}")

today_completed = today_all.filter(status='completed')
print(f"  - Completed today: {today_completed.count()}")

today_without_lpg = today_completed.exclude(fuel_type__name__iexact='lpg')
print(f"  - Completed (excluding LPG): {today_without_lpg.count()}")

# Revenue calculation (same as dashboard)
today_revenue = today_without_lpg.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
print(f"  - Today's revenue (dashboard query): GH₡{today_revenue}")

# Show actual transactions
if today_without_lpg.count() > 0:
    print("\n💳 Today's completed transactions (excluding LPG):")
    for txn in today_without_lpg:
        print(f"  - {txn.transaction_id}: {txn.liters_dispensed}L @ GH₡{txn.price_per_liter}/L = GH₡{txn.total_amount}")
        print(f"    Fuel: {txn.fuel_type.name}, Status: {txn.status}, Time: {txn.created_at}")
else:
    print("\n❌ No completed transactions found for today")

# Check for incomplete transactions today
print("\n⚠️  Incomplete transactions today:")
incomplete_today = today_all.exclude(status='completed')
if incomplete_today.count() > 0:
    for txn in incomplete_today:
        print(f"  - {txn.transaction_id}: Status={txn.status}, Amount=GH₡{txn.total_amount}")
else:
    print("  - None")

# Check recent transactions (last 24 hours)
print("\n🕐 Transactions from last 24 hours:")
yesterday = now - timedelta(hours=24)
last_24h = Transaction.objects.filter(created_at__gte=yesterday)
print(f"  - Total: {last_24h.count()}")
if last_24h.count() > 0:
    for txn in last_24h.order_by('-created_at')[:5]:
        print(f"    {txn.created_at}: {txn.transaction_id} (Status: {txn.status}) = GH₡{txn.total_amount}")

# Check fuel types
print("\n⛽ Fuel types:")
for fuel in FuelType.objects.all():
    price = fuel.current_price
    print(f"  - {fuel.name}: GH₡{price}/L")

# Yesterday's revenue for comparison
yesterday_date = today - timedelta(days=1)
yesterday_txns = Transaction.objects.filter(
    created_at__date=yesterday_date,
    status='completed'
).exclude(fuel_type__name__iexact='lpg')
yesterday_revenue = yesterday_txns.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
print(f"\n📊 Yesterday's revenue ({yesterday_date}): GH₡{yesterday_revenue}")

print("\n" + "=" * 70)
if today_without_lpg.count() == 0:
    print("⚠️  ISSUE FOUND: No completed transactions for today")
    print("   Possible causes:")
    print("   1. Transactions not being created at all")
    print("   2. Transactions being created with wrong status")
    print("   3. Transactions being created for wrong date/timezone")
    print("   4. All transactions are LPG type (excluded from dashboard)")
else:
    print("✅ Revenue data looks correct")
print("=" * 70)
