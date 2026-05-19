import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from station.models import FuelType, Pump, FuelInventory

# Create fuel types
fuel_types = [
    {'name': 'Petrol', 'price': Decimal('12.50')},
    {'name': 'Diesel', 'price': Decimal('11.75')},
    {'name': 'LPG', 'price': Decimal('9.20')},
]

print('Creating fuel types...')
for fuel_data in fuel_types:
    fuel_type, created = FuelType.objects.get_or_create(
        name=fuel_data['name'],
        defaults={'current_price': fuel_data['price']}
    )
    if created:
        print(f'✓ Created {fuel_data["name"]} @ GH₵{fuel_data["price"]}')
    else:
        print(f'✓ {fuel_data["name"]} already exists')

# Create pumps
print('\nCreating pumps...')
from datetime import date
fuel_type = FuelType.objects.first()  # Get first fuel type

for pump_num in range(1, 4):
    pump, created = Pump.objects.get_or_create(
        pump_number=str(pump_num),
        defaults={
            'status': 'operational',
            'fuel_type': fuel_type,
            'installation_date': date.today()
        }
    )
    if created:
        print(f'✓ Created Pump {pump_num}')
    else:
        print(f'✓ Pump {pump_num} already exists')

# Create fuel inventory for each fuel type
print('\nCreating fuel inventory...')
for fuel in FuelType.objects.all():
    inventory, created = FuelInventory.objects.get_or_create(
        fuel_type=fuel,
        defaults={
            'quantity_liters': Decimal('5000'),
            'max_capacity': Decimal('10000')
        }
    )
    if created:
        print(f'✓ Created inventory for {fuel.name}: 5000L / 10000L')
    else:
        print(f'✓ Inventory for {fuel.name} already exists')

print('\n✅ Station setup complete! You can now record transactions.')
