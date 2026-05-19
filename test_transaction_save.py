import os
import django
from decimal import Decimal
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from station.models import Transaction, Pump, FuelType, FuelInventory, Customer, Staff
from django.db import transaction as db_transaction
import uuid

print("=== Testing Transaction Creation ===\n")

try:
    with db_transaction.atomic():
        # Get test pump
        pump = Pump.objects.first()
        print(f"✓ Got pump: {pump.pump_number if pump else 'None'}")
        
        if not pump:
            print("✗ No pump found!")
            exit(1)
        
        # Get test fuel type
        fuel_type = FuelType.objects.exclude(name__iexact='lpg').first()
        print(f"✓ Got fuel type: {fuel_type.name if fuel_type else 'None'}")
        
        if not fuel_type:
            print("✗ No fuel type found!")
            exit(1)
        
        # Check fuel inventory
        fuel_inventory = FuelInventory.objects.select_for_update().get(fuel_type=fuel_type)
        print(f"✓ Got fuel inventory: {fuel_inventory.quantity_liters}L available")
        
        if fuel_inventory.quantity_liters < 1:
            print("✗ Insufficient fuel!")
            exit(1)
        
        # Get staff
        staff = Staff.objects.first()
        print(f"✓ Got staff: {staff}")
        
        # Create transaction
        transaction_id = str(uuid.uuid4())[:8].upper()
        liters = Decimal('10')
        total_amount = liters * fuel_type.current_price
        
        print(f"\nCreating transaction:")
        print(f"  ID: {transaction_id}")
        print(f"  Liters: {liters}")
        print(f"  Price per liter: {fuel_type.current_price}")
        print(f"  Total: {total_amount}")
        print(f"  Status: completed")
        print(f"  Created at: {timezone.now()}")
        
        txn = Transaction.objects.create(
            transaction_id=transaction_id,
            pump=pump,
            fuel_type=fuel_type,
            liters_dispensed=liters,
            price_per_liter=fuel_type.current_price,
            total_amount=total_amount,
            payment_method='cash',
            status='completed',
            staff=staff,
            reference_number=f"REF-{transaction_id}",
            completed_at=timezone.now(),
        )
        
        print(f"\n✓ Transaction created successfully!")
        print(f"  DB ID: {txn.id}")
        print(f"  Transaction ID: {txn.transaction_id}")
        print(f"  Created at: {txn.created_at}")
        
        # Verify it's in the database
        fetched_txn = Transaction.objects.filter(transaction_id=transaction_id).first()
        if fetched_txn:
            print(f"✓ Transaction verified in database")
        else:
            print(f"✗ Transaction NOT found in database!")
            
except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n=== Checking today's transactions ===")
today = timezone.localdate()
today_txns = Transaction.objects.filter(created_at__date=today, status='completed')
print(f"Completed transactions today: {today_txns.count()}")
for txn in today_txns:
    print(f"  {txn.transaction_id} - {txn.total_amount} - {txn.created_at}")
