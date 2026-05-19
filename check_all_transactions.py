import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all transactions with full details
cursor.execute('''
    SELECT 
        st.id, st.transaction_id, st.status, st.total_amount, st.liters_dispensed,
        st.created_at, st.completed_at,
        sp.pump_number,
        ft.name as fuel_type,
        sc.first_name || ' ' || sc.last_name as customer_name,
        ss.user_id, su.username
    FROM station_transaction st
    LEFT JOIN station_pump sp ON st.pump_id = sp.id
    LEFT JOIN station_fueltype ft ON st.fuel_type_id = ft.id
    LEFT JOIN station_customer sc ON st.customer_id = sc.id
    LEFT JOIN station_staff ss ON st.staff_id = ss.id
    LEFT JOIN auth_user su ON ss.user_id = su.id
    ORDER BY st.created_at DESC
''')

transactions = cursor.fetchall()
print(f'Total transactions: {len(transactions)}\n')

if transactions:
    for txn in transactions:
        print(f'ID: {txn[0]}, TX: {txn[1]}')
        print(f'  Status: {txn[2]}')
        print(f'  Amount: GH₵{txn[3]}, Liters: {txn[4]}L')
        print(f'  Created: {txn[5]}')
        print(f'  Completed: {txn[6]}')
        print(f'  Pump: {txn[7]}')
        print(f'  Fuel: {txn[8]}')
        print(f'  Customer: {txn[9]}')
        print(f'  Staff: {txn[11]} (User ID: {txn[10]})')
        print()

# Check status distribution
cursor.execute('SELECT status, COUNT(*) FROM station_transaction GROUP BY status')
statuses = cursor.fetchall()
print('Transaction statuses:')
for status, count in statuses:
    print(f'  {status}: {count}')

conn.close()
