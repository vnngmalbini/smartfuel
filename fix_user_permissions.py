#!/usr/bin/env python
"""Fix user role permissions for fuel sales"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from dashboard.models import UserProfile
from station.models import Staff, StaffRole

print("=" * 70)
print("FIXING USER PERMISSIONS FOR FUEL SALES")
print("=" * 70)

# Get veronica.ngmalbini
user = User.objects.get(username='veronica.ngmalbini')
print(f"\nUser: {user.username}")

# Update or create UserProfile with admin role
profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={'role': 'admin'}
)

if not created:
    print(f"UserProfile exists with role: {profile.role}")
    if profile.role != 'admin':
        profile.role = 'admin'
        profile.save()
        print(f"✓ Updated role to: admin")
    else:
        print(f"✓ Role already set to: admin")
else:
    print(f"✓ Created UserProfile with role: admin")

# Check for Staff profile
try:
    staff = Staff.objects.get(user=user)
    print(f"✓ Staff profile exists with role: {staff.role.name}")
except Staff.DoesNotExist:
    print(f"Note: No Staff profile (optional for admin users)")

print("\n" + "=" * 70)
print("✅ User permissions fixed!")
print("   veronica.ngmalbini now has role='admin'")
print("   Can now access fuel sales and other admin features")
print("=" * 70)
