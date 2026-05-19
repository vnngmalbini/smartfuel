import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if any users are superusers
cursor.execute('''
    SELECT id, username, first_name, last_name, is_superuser, is_staff 
    FROM auth_user
    ORDER BY id DESC
''')

users = cursor.fetchall()
print('Users and their superuser status:')
for user in users:
    print(f'  ID: {user[0]}, {user[1]}: superuser={user[4]}, staff={user[5]}')

# Check UserProfile roles
cursor.execute('''
    SELECT u.id, u.username, up.role
    FROM auth_user u
    LEFT JOIN dashboard_userprofile up ON u.id = up.user_id
    ORDER BY u.id DESC
''')

profiles = cursor.fetchall()
print('\nUserProfile roles:')
for p in profiles:
    print(f'  ID: {p[0]}, {p[1]}: role={p[2]}')

conn.close()
