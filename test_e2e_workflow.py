#!/usr/bin/env python
"""
End-to-end test of the fuel sale workflow
This simulates a user going through: start → form → review → complete
"""

import os
import django
import traceback
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from station.models import (
    Pump, FuelType, FuelInventory, Transaction as StationTransaction, 
    Staff, StaffRole
)

client = Client()

print("=" * 70)
print("END-TO-END FUEL SALE WORKFLOW TEST")
print("=" * 70)

try:
    # Setup test user with proper staff profile
    print("\n1. Setting up test user with staff profile...")
    user, created = User.objects.get_or_create(
        username='e2e_test_attendant',
        defaults={
            'first_name': 'E2E',
            'last_name': 'Attendant',
            'email': 'e2e@test.com',
            'is_active': True,
        }
    )
    user.set_password('testpass123')
    user.save()
    print(f"   User: {user.username}")
    
    # Ensure staff profile exists
    if not hasattr(user, 'staff_profile'):
        role, _ = StaffRole.objects.get_or_create(
            name='attendant',
            defaults={'permissions': 'fuel_sale,view_dashboard'}
        )
        staff, _ = Staff.objects.get_or_create(
            user=user,
            defaults={
                'role': role,
                'phone': '0123456789',
                'date_hired': timezone.now().date(),
            }
        )
        print(f"   Created staff profile: {staff.role.name}")
    else:
        staff = user.staff_profile
        print(f"   Staff profile exists: {staff.role.name}")
    
    # Get test pump and fuel
    pump = Pump.objects.filter(status='operational').first()
    if not pump:
        print("   ❌ No operational pump available")
        exit(1)
    print(f"   Pump: {pump.pump_number}")
    
    fuel_type = FuelType.objects.exclude(name__iexact='lpg').first()
    if not fuel_type:
        print("   ❌ No fuel types available")
        exit(1)
    print(f"   Fuel type: {fuel_type.name}")
    
    # Login
    print("\n2. Logging in...")
    login_success = client.login(username='e2e_test_attendant', password='testpass123')
    if not login_success:
        print("   ❌ Login failed")
        exit(1)
    print("   ✓ Logged in successfully")
    
    # Step 1: Start fuel sale
    print("\n3. Starting fuel sale...")
    response = client.get('/fuel-sale/start/', follow=True)
    if response.status_code != 200:
        print(f"   ❌ Failed to load start page (status: {response.status_code})")
        print(f"   Response: {response.content[:200]}")
    else:
        print(f"   ✓ Start page loaded (status: {response.status_code})")
    
    # Step 2: Submit fuel sale form
    print("\n4. Submitting fuel sale form...")
    form_data = {
        'fuel_type': fuel_type.id,
        'liters_dispensed': '25.00',
        'payment_method': 'cash',
        'customer_phone': '',
        'notes': 'E2E test transaction',
    }
    response = client.post(f'/fuel-sale/{pump.id}/', data=form_data, follow=True)
    print(f"   Response status: {response.status_code}")
    print(f"   Redirected to: {response.request['PATH_INFO']}")
    
    if '/fuel-sale/review/' not in response.request['PATH_INFO']:
        print(f"   ❌ Not redirected to review page")
        if hasattr(response, 'content'):
            print(f"   Response content: {response.content[:500]}")
    else:
        print(f"   ✓ Redirected to review page")
    
    # Step 3: Check session data
    print("\n5. Checking session data...")
    if 'fuel_sale_data' in client.session:
        session_data = client.session['fuel_sale_data']
        print(f"   ✓ Session data found:")
        for key, value in session_data.items():
            print(f"      {key}: {value}")
    else:
        print(f"   ❌ No session data found")
        print(f"   Available session keys: {list(client.session.keys())}")
    
    # Step 4: Submit review form (complete the transaction)
    print("\n6. Completing transaction...")
    response = client.post('/fuel-sale/complete/', {}, follow=True)
    print(f"   Response status: {response.status_code}")
    print(f"   Redirected to: {response.request['PATH_INFO']}")
    
    # Step 5: Check if transaction was created
    print("\n7. Verifying transaction creation...")
    today = timezone.localdate()
    today_txns = StationTransaction.objects.filter(
        created_at__date=today,
        status='completed'
    ).exclude(fuel_type__name__iexact='lpg')
    
    print(f"   Transactions created today: {today_txns.count()}")
    if today_txns.count() > 0:
        for txn in today_txns:
            print(f"      - {txn.transaction_id}: {txn.liters_dispensed}L @ GH₡{txn.total_amount}")
        
        today_revenue = today_txns.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        print(f"   ✅ Today's revenue (dashboard query): GH₡{today_revenue}")
    else:
        print(f"   ❌ No transactions created")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()

finally:
    # Logout
    client.logout()
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
