import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check fuel types
cursor.execute('SELECT COUNT(*) FROM station_fueltype')
fuel_types = cursor.fetchone()[0]
print(f'Fuel types configured: {fuel_types}')

if fuel_types > 0:
    cursor.execute('SELECT id, name, current_price FROM station_fueltype')
    for row in cursor.fetchall():
        print(f'  - {row[1]}: GH₵{row[2]} (ID: {row[0]})')

# Check pumps
cursor.execute('SELECT COUNT(*) FROM station_pump')
pumps = cursor.fetchone()[0]
print(f'\nPumps configured: {pumps}')

if pumps > 0:
    cursor.execute('SELECT id, pump_number, status FROM station_pump')
    for row in cursor.fetchall():
        print(f'  - Pump {row[1]}: {row[2]} (ID: {row[0]})')

# Check fuel inventory
cursor.execute('SELECT COUNT(*) FROM station_fuelinventory')
inventory = cursor.fetchone()[0]
print(f'\nFuel inventory records: {inventory}')

if inventory > 0:
    cursor.execute('''
        SELECT fi.id, ft.name, fi.quantity_liters, fi.max_capacity 
        FROM station_fuelinventory fi
        JOIN station_fueltype ft ON fi.fuel_type_id = ft.id
    ''')
    for row in cursor.fetchall():
        print(f'  - {row[1]}: {row[2]}L / {row[3]}L (ID: {row[0]})')

conn.close()
