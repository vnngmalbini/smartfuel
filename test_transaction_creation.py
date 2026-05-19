#!/usr/bin/env python
"""Test transaction creation with detailed logging"""

import os
import django
import traceback
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from station.models import (
    Pump, FuelType, FuelInventory, Customer, Staff, 
    Transaction as StationTransaction, Receipt
)

print("=" * 70)
print("TESTING TRANSACTION CREATION")
print("=" * 70)

# Setup
pump = None
fuel_type = None
inventory = None
staff = None
user = None

try:
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='test_attendant',
        defaults={
            'first_name': 'Test',
            'last_name': 'Attendant',
            'email': 'test@example.com'
        }
    )
    print(f"✓ User: {user.username}")
    
    # Get pump
    pump = Pump.objects.filter(status='operational').first()
    if not pump:
        print("❌ No operational pumps found!")
        pumps_list = Pump.objects.all()
        print(f"   Available pumps: {pumps_list.count()}")
        for p in pumps_list:
            print(f"     - {p.pump_number}: {p.status}")
        exit(1)
    print(f"✓ Pump: {pump.pump_number} ({pump.fuel_type.name})")
    
    # Get fuel type
    fuel_type = FuelType.objects.exclude(name__iexact='lpg').first()
    if not fuel_type:
        print("❌ No fuel types found!")
        exit(1)
    print(f"✓ Fuel type: {fuel_type.name} @ GH₡{fuel_type.current_price}/L")
    
    # Check inventory
    try:
        inventory = FuelInventory.objects.get(fuel_type=fuel_type)
        print(f"✓ Inventory: {inventory.quantity_liters}L available")
    except FuelInventory.DoesNotExist:
        print(f"❌ No inventory for {fuel_type.name}")
        exit(1)
    
    # Get staff profile
    try:
        staff = user.staff_profile
        print(f"✓ Staff profile: {staff.role}")
    except:
        print("⚠ No staff profile (will create with None)")
        staff = None
    
    # Now test transaction creation
    print("\n" + "=" * 70)
    print("ATTEMPTING TRANSACTION CREATION")
    print("=" * 70)
    
    import uuid
    transaction_id = str(uuid.uuid4())[:8].upper()
    liters = Decimal('25.00')
    total_amount = liters * fuel_type.current_price
    
    print(f"Transaction ID: {transaction_id}")
    print(f"Liters: {liters}")
    print(f"Price per liter: {fuel_type.current_price}")
    print(f"Total amount: {total_amount}")
    print(f"Pump: {pump.pump_number}")
    print(f"Fuel type: {fuel_type.name}")
    print(f"Status: completed")
    print(f"Timestamp: {timezone.now()}")
    
    print("\nCreating transaction...")
    
    # Try to create the transaction with the same code as fuel_sale_complete
    txn = StationTransaction.objects.create(
        transaction_id=transaction_id,
        pump=pump,
        customer=None,
        fuel_type=fuel_type,
        liters_dispensed=liters,
        price_per_liter=fuel_type.current_price,
        total_amount=total_amount,
        payment_method='cash',
        status='completed',
        staff=staff,
        reference_number=f"REF-{transaction_id}",
        notes='Test transaction',
        completed_at=timezone.now(),
    )
    
    print(f"✅ Transaction created!")
    print(f"   DB ID: {txn.id}")
    print(f"   Created at: {txn.created_at}")
    print(f"   Status: {txn.status}")
    
    # Verify it was saved
    saved_txn = StationTransaction.objects.get(id=txn.id)
    print(f"✅ Transaction verified in database!")
    
    # Check if it appears in dashboard query
    from django.db.models import Sum
    today = timezone.localdate()
    today_txns = StationTransaction.objects.filter(
        created_at__date=today,
        status='completed'
    ).exclude(fuel_type__name__iexact='lpg')
    print(f"✅ Dashboard query result: {today_txns.count()} transactions")
    
    today_revenue = today_txns.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    print(f"✅ Today's revenue (from dashboard query): GH₡{today_revenue}")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
