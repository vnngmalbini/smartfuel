#!/usr/bin/env python
"""Check current user roles and profiles"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from dashboard.models import UserProfile
from station.models import Staff

print("=" * 70)
print("USER PROFILES & ROLES DIAGNOSTIC")
print("=" * 70)

# Find the main user (likely Veronica)
veronica = None
users = User.objects.all()
print(f"\nTotal users in system: {users.count()}\n")

for user in users:
    print(f"User: {user.username}")
    print(f"  Full name: {user.get_full_name()}")
    print(f"  Email: {user.email}")
    print(f"  Superuser: {user.is_superuser}")
    
    # Check for UserProfile
    try:
        profile = UserProfile.objects.get(user=user)
        print(f"  ✓ UserProfile role: {profile.role}")
    except UserProfile.DoesNotExist:
        print(f"  ✗ No UserProfile")
    
    # Check for Staff profile
    try:
        staff = Staff.objects.get(user=user)
        print(f"  ✓ Staff role: {staff.role.name}")
    except Staff.DoesNotExist:
        print(f"  ✗ No Staff profile")
    
    # Show if this looks like the main user
    if 'veronica' in user.username.lower() or user.is_superuser:
        veronica = user
        print(f"  >>> MAIN USER <<<")
    
    print()

print("\n" + "=" * 70)
print("RECOMMENDATIONS")
print("=" * 70)

if veronica:
    print(f"\nMain user appears to be: {veronica.username}")
    
    # Check if they have proper profiles
    has_userprofile = UserProfile.objects.filter(user=veronica).exists()
    has_staff = Staff.objects.filter(user=veronica).exists()
    
    if not has_userprofile:
        print(f"❌ No UserProfile - this is why fuel sales don't work!")
        print(f"   Need to create UserProfile with role='attendant' or 'admin'")
    else:
        profile = UserProfile.objects.get(user=veronica)
        if profile.role not in ['admin', 'attendant', 'manager']:
            print(f"⚠ UserProfile role is '{profile.role}' - should be admin/attendant/manager")
    
    if not has_staff:
        print(f"⚠ No Staff profile - may cause issues with staff tracking")
else:
    print("Could not identify main user")

print("\n" + "=" * 70)
