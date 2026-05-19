import os
import django
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from station.models import (
    Pump, FuelType, FuelInventory, Customer, Staff, Transaction as StationTransaction,
    Receipt
)
from django.contrib.auth.models import User

# Simulate the fuel_sale_complete logic
print("=== Simulating fuel_sale_complete flow ===\n")

try:
    user = User.objects.get(username='user_5022447')
    print(f'User: {user.username}')
    
    # Simulate session data
    fuel_sale_data = {
        'pump_id': 1,
        'fuel_type_id': 1,
        'liters': '75.50',
        'payment_method': 'cash',
        'customer_phone': '',
        'notes': 'Test transaction from web flow',
    }
    
    with db_transaction.atomic():
        print('\n--- Starting transaction ---')
        
        # Get objects
        pump = Pump.objects.get(id=fuel_sale_data['pump_id'])
        fuel_type = FuelType.objects.get(id=fuel_sale_data['fuel_type_id'])
        liters = Decimal(fuel_sale_data['liters'])
        
        print(f'Pump: {pump.pump_number}')
        print(f'Fuel type: {fuel_type.name}')
        print(f'Liters: {liters}')
        
        # Check fuel availability
        fuel_inventory = FuelInventory.objects.select_for_update().get(fuel_type=fuel_type)
        print(f'Available inventory: {fuel_inventory.quantity_liters}L')
        
        if fuel_inventory.quantity_liters < liters:
            print(f'ERROR: Insufficient fuel!')
            raise Exception(f'Insufficient fuel. Available: {fuel_inventory.quantity_liters}L')
        
        # Create transaction
        transaction_id = str(uuid.uuid4())[:8].upper()
        total_amount = liters * fuel_type.current_price
        
        print(f'Transaction ID: {transaction_id}')
        print(f'Total amount: {total_amount}')
        
        # Get customer if exists
        customer = None
        if fuel_sale_data.get('customer_phone'):
            customer, _ = Customer.objects.get_or_create(
                phone=fuel_sale_data['customer_phone'],
                defaults={'first_name': 'Customer', 'last_name': fuel_sale_data['customer_phone']}
            )
        
        # Get staff
        staff = user.staff_profile if hasattr(user, 'staff_profile') else None
        print(f'Staff: {staff}')
        
        # Create transaction
        print('\nCreating transaction...')
        txn = StationTransaction.objects.create(
            transaction_id=transaction_id,
            pump=pump,
            customer=customer,
            fuel_type=fuel_type,
            liters_dispensed=liters,
            price_per_liter=fuel_type.current_price,
            total_amount=total_amount,
            payment_method=fuel_sale_data['payment_method'],
            status='completed',
            staff=staff,
            reference_number=f"REF-{transaction_id}",
            notes=fuel_sale_data.get('notes', ''),
            completed_at=timezone.now(),
        )
        print(f'✅ Transaction created: {txn.id}')
        
        # Update fuel inventory
        fuel_inventory.quantity_liters -= liters
        fuel_inventory.save()
        print(f'✅ Inventory updated: {fuel_inventory.quantity_liters}L remaining')
        
        # Update pump metrics
        pump.total_liters_dispensed += liters
        pump.total_revenue += total_amount
        pump.save()
        print(f'✅ Pump updated')
        
        # Create receipt
        receipt_number = f"RCP-{transaction_id}"
        loyalty_points = int(liters)
        
        receipt = Receipt.objects.create(
            transaction=txn,
            receipt_number=receipt_number,
            loyalty_points_earned=loyalty_points,
            final_amount=total_amount,
        )
        print(f'✅ Receipt created: {receipt_number}')
        
        # Update customer loyalty points if exists
        if customer:
            customer.loyalty_points += loyalty_points
            customer.total_purchases += total_amount
            customer.total_liters += liters
            customer.save()
            print(f'✅ Customer loyalty points updated')
        
        print(f'\n✅ TRANSACTION COMPLETED SUCCESSFULLY!')
        print(f'Receipt: {receipt_number}')
        
except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()

# Now check if it's in the database
print('\n=== Checking database ===')

from django.db.models import Sum
today = timezone.localdate()
start_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
end_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

period_transactions = StationTransaction.objects.filter(
    created_at__gte=start_dt,
    created_at__lte=end_dt,
    status='completed',
)

count = period_transactions.count()
revenue = period_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

print(f'Completed transactions today: {count}')
print(f'Today revenue: {revenue}')
