import sqlite3
from datetime import datetime, timedelta
import os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check total transactions
cursor.execute('SELECT COUNT(*) FROM station_transaction')
total = cursor.fetchone()[0]
print(f'Total transactions: {total}')

# Get recent transactions
cursor.execute('''
    SELECT id, transaction_id, status, total_amount, created_at 
    FROM station_transaction 
    ORDER BY created_at DESC 
    LIMIT 5
''')

rows = cursor.fetchall()
if rows:
    print('\nRecent transactions:')
    for row in rows:
        print(f'  ID: {row[0]}, TX: {row[1]}, Status: {row[2]}, Amount: {row[3]}, Created: {row[4]}')
else:
    print('No transactions found')

# Check today's transactions (UTC and local)
cursor.execute('''
    SELECT COUNT(*) FROM station_transaction 
    WHERE DATE(created_at) = DATE('now')
''')
today_count = cursor.fetchone()[0]
print(f'\nTransactions today (UTC): {today_count}')

conn.close()
