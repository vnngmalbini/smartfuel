import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check total transactions
cursor.execute('SELECT COUNT(*) FROM station_transaction')
total = cursor.fetchone()[0]
print(f'Total transactions in database: {total}')

# Get all transactions with details
cursor.execute('''
    SELECT id, transaction_id, status, total_amount, liters_dispensed, created_at, pump_id, fuel_type_id
    FROM station_transaction 
    ORDER BY created_at DESC 
    LIMIT 10
''')

rows = cursor.fetchall()
if rows:
    print('\nAll transactions:')
    for row in rows:
        print(f'  ID: {row[0]}, TX: {row[1]}, Status: {row[2]}, Amount: {row[3]}, Liters: {row[4]}, Created: {row[5]}, Pump: {row[6]}, Fuel Type: {row[7]}')
else:
    print('No transactions found')

# Check transaction statuses
cursor.execute('SELECT DISTINCT status FROM station_transaction')
statuses = cursor.fetchall()
if statuses:
    print(f'\nTransaction statuses in database: {[s[0] for s in statuses]}')

# Check today's transactions by various date interpretations
print('\n--- Transaction counts by date filter ---')

cursor.execute('''
    SELECT COUNT(*) FROM station_transaction 
    WHERE DATE(created_at) = DATE('now')
''')
today_utc = cursor.fetchone()[0]
print(f'Today (UTC): {today_utc}')

cursor.execute('''
    SELECT COUNT(*) FROM station_transaction 
    WHERE DATE(created_at) = DATE('now', 'localtime')
''')
today_local = cursor.fetchone()[0]
print(f'Today (local): {today_local}')

cursor.execute('''
    SELECT COUNT(*) FROM station_transaction 
    WHERE status = 'completed'
''')
completed = cursor.fetchone()[0]
print(f'Completed transactions (all time): {completed}')

cursor.execute('''
    SELECT COUNT(*) FROM station_transaction 
    WHERE status = 'completed' AND DATE(created_at) = DATE('now')
''')
completed_today = cursor.fetchone()[0]
print(f'Completed transactions today (UTC): {completed_today}')

conn.close()
