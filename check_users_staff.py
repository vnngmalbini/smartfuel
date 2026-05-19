import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check users
cursor.execute('SELECT COUNT(*) FROM auth_user')
user_count = cursor.fetchone()[0]
print(f'Total users: {user_count}')

# Get user details
cursor.execute('''
    SELECT id, username, first_name, last_name, email 
    FROM auth_user
    ORDER BY id DESC
    LIMIT 5
''')

users = cursor.fetchall()
if users:
    print('\nUsers:')
    for user in users:
        print(f'  ID: {user[0]}, Username: {user[1]}, Name: {user[2]} {user[3]}, Email: {user[4]}')

# Check staff members
cursor.execute('SELECT COUNT(*) FROM station_staff')
staff_count = cursor.fetchone()[0]
print(f'\nTotal staff profiles: {staff_count}')

if staff_count > 0:
    cursor.execute('''
        SELECT s.id, s.user_id, u.username, u.first_name, u.last_name, r.name, s.is_active
        FROM station_staff s
        JOIN auth_user u ON s.user_id = u.id
        LEFT JOIN station_staffrole r ON s.role_id = r.id
    ''')
    
    staff = cursor.fetchall()
    print('\nStaff profiles:')
    for s in staff:
        print(f'  ID: {s[0]}, User: {s[2]} ({s[1]}), Name: {s[3]} {s[4]}, Role: {s[5]}, Active: {s[6]}')

# Check if any of the users have staff profile
cursor.execute('''
    SELECT COUNT(*) FROM auth_user au
    LEFT JOIN station_staff ss ON au.id = ss.user_id
    WHERE ss.id IS NULL
''')
no_staff = cursor.fetchone()[0]
print(f'\nUsers WITHOUT staff profile: {no_staff}')

# List users without staff profile
cursor.execute('''
    SELECT au.id, au.username FROM auth_user au
    LEFT JOIN station_staff ss ON au.id = ss.user_id
    WHERE ss.id IS NULL
''')
users_no_staff = cursor.fetchall()
if users_no_staff:
    print('  Users without staff profile:')
    for u in users_no_staff:
        print(f'    - {u[1]} (ID: {u[0]})')

conn.close()
