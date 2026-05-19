import os
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from station.models import Pump, FuelType, FuelInventory, Customer, Staff, Transaction
from django.contrib.auth.models import User

try:
    # Get user
    user = User.objects.get(username='user_5022447')
    print(f'User: {user.username}')
    
    # Get pump
    pump = Pump.objects.first()
    print(f'Pump: {pump.pump_number}')
    
    # Get fuel type
    fuel_type = FuelType.objects.first()
    print(f'Fuel type: {fuel_type.name}')
    
    # Check inventory
    inventory = FuelInventory.objects.get(fuel_type=fuel_type)
    print(f'Inventory: {inventory.quantity_liters}L available')
    
    # Get staff profile
    try:
        staff = user.staff_profile
        print(f'Staff profile: {staff.role}')
    except:
        staff = None
        print('No staff profile for user')
    
    # Try to create a transaction
    import uuid
    transaction_id = str(uuid.uuid4())[:8].upper()
    liters = Decimal('50.00')
    total_amount = liters * fuel_type.current_price
    
    print(f'\n--- Creating transaction ---')
    print(f'Transaction ID: {transaction_id}')
    print(f'Liters: {liters}')
    print(f'Price per liter: {fuel_type.current_price}')
    print(f'Total amount: {total_amount}')
    
    txn = Transaction.objects.create(
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
    
    print(f'\n✅ Transaction created successfully!')
    print(f'Transaction ID in DB: {txn.id}')
    print(f'Created at: {txn.created_at}')
    
    # Verify it was saved
    saved_txn = Transaction.objects.get(id=txn.id)
    print(f'\n✅ Transaction verified in database!')
    print(f'Status: {saved_txn.status}')
    print(f'Amount: {saved_txn.total_amount}')
    
except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
