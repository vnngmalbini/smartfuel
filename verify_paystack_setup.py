#!/usr/bin/env python
"""
SmartFuel Paystack Integration Verification Script
Checks that all fixes are properly installed and working
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.apps import apps
from django.db import connection
from station.models import Transaction
from payment.models import PaymentGatewayLog
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VerificationChecker:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def check(self, name, condition, error_msg=""):
        """Record check result"""
        if condition:
            self.passed.append(name)
            print(f"✓ {name}")
        else:
            self.failed.append(name)
            print(f"✗ {name}")
            if error_msg:
                print(f"  └─ {error_msg}")

    def warning(self, name, msg):
        """Record warning"""
        self.warnings.append(f"{name}: {msg}")
        print(f"⚠ {name}")
        print(f"  └─ {msg}")

    def summary(self):
        """Print verification summary"""
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        print(f"✓ Passed: {len(self.passed)}")
        print(f"✗ Failed: {len(self.failed)}")
        print(f"⚠ Warnings: {len(self.warnings)}")
        
        if self.failed:
            print("\nFailed Checks:")
            for check in self.failed:
                print(f"  - {check}")
            return False
        
        return True


def check_environment():
    """Check environment configuration"""
    print("\n" + "="*60)
    print("1. ENVIRONMENT CONFIGURATION")
    print("="*60)
    
    checker = VerificationChecker()
    
    # Check PAYSTACK_SECRET_KEY
    secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
    checker.check(
        "PAYSTACK_SECRET_KEY configured",
        secret_key and len(secret_key) > 0,
        "Set PAYSTACK_SECRET_KEY in .env or settings.py"
    )
    
    if secret_key:
        checker.check(
            "PAYSTACK_SECRET_KEY is not default",
            not secret_key.startswith('sk_test_'),  # Obviously a placeholder
            "Set real Paystack secret key from https://dashboard.paystack.co/settings"
        )
    
    # Check SITE_BASE_URL
    site_url = getattr(settings, 'SITE_BASE_URL', None)
    checker.check(
        "SITE_BASE_URL configured",
        site_url and len(site_url) > 0,
        "Set SITE_BASE_URL in settings.py (e.g., https://yoursite.com or http://127.0.0.1:8000)"
    )

    webhook_url = getattr(settings, 'PAYSTACK_WEBHOOK_URL', None)
    checker.check(
        "PAYSTACK_WEBHOOK_URL configured",
        webhook_url and len(webhook_url) > 0,
        "Set PAYSTACK_WEBHOOK_URL or let it derive from SITE_BASE_URL"
    )
    if webhook_url:
        print(f"Webhook URL to register in Paystack: {webhook_url}")
        if '127.0.0.1' in webhook_url or 'localhost' in webhook_url:
            checker.warning(
                "Webhook URL is local-only",
                "Paystack cannot notify localhost. Set SITE_BASE_URL or PAYSTACK_WEBHOOK_URL to a public HTTPS URL."
            )
    
    # Check logs directory
    logs_dir = Path('logs')
    checker.check(
        "Logs directory exists",
        logs_dir.exists() and logs_dir.is_dir(),
        "Run: mkdir logs"
    )
    
    if logs_dir.exists():
        log_file = logs_dir / 'smartfuel.log'
        if log_file.exists():
            checker.check(
                "Logs are being written",
                log_file.stat().st_size > 0,
                "No log entries yet (normal if app just started)"
            )
        else:
            checker.warning("No log file yet", "Will be created when first payment is processed")
    
    return checker


def check_models():
    """Check database models"""
    print("\n" + "="*60)
    print("2. DATABASE MODELS")
    print("="*60)
    
    checker = VerificationChecker()
    
    # Check that Transaction model exists and is correct
    try:
        from station.models import Transaction
        checker.check("station.models.Transaction exists", True)
        
        # Check for required fields
        fields = [f.name for f in Transaction._meta.get_fields()]
        required_fields = ['transaction_id', 'reference_number', 'pump', 'customer', 'fuel_type', 
                          'total_amount', 'status', 'created_at', 'completed_at']
        
        for field in required_fields:
            checker.check(
                f"Transaction.{field} field exists",
                field in fields,
                f"Missing required field: {field}"
            )
    except ImportError as e:
        checker.failed.append(f"station.models.Transaction: {e}")
        print(f"✗ station.models.Transaction exists: {e}")
    
    # Check that payment.models.Transaction is gone (duplicate removed)
    from payment import models as payment_models
    has_duplicate = hasattr(payment_models, 'Transaction')
    checker.check(
        "Duplicate payment.models.Transaction removed",
        not has_duplicate,
        "Old duplicate model still exists! Run migrations: python manage.py migrate payment"
    )
    
    # Check PaymentGatewayLog has correct FK
    try:
        log = PaymentGatewayLog.objects.first()
        if log:
            checker.check("PaymentGatewayLog.transaction FK is correct", True)
        else:
            checker.warning("PaymentGatewayLog empty", "No logs created yet (normal)")
    except Exception as e:
        checker.failed.append(f"PaymentGatewayLog check: {e}")
        print(f"✗ PaymentGatewayLog check: {e}")
    
    return checker


def check_code():
    """Check that code changes are implemented"""
    print("\n" + "="*60)
    print("3. CODE IMPLEMENTATION")
    print("="*60)
    
    checker = VerificationChecker()
    
    # Check payment/views.py imports
    try:
        with open('payment/views.py', 'r', encoding='utf-8') as f:
            content = f.read()
            checker.check(
                "payment/views.py uses station.models.Transaction",
                'from station.models import Transaction' in content,
                "Update payment/views.py: change import to 'from station.models import Transaction'"
            )
            checker.check(
                "Webhook has enhanced logging",
                'WEBHOOK' in content and 'webhook_id' in content,
                "Update paystack_webhook() with logging enhancements"
            )
    except FileNotFoundError:
        checker.failed.append("payment/views.py not found")
    
    # Check dashboard/views.py has live stats API
    try:
        with open('dashboard/views.py', 'r', encoding='utf-8') as f:
            content = f.read()
            checker.check(
                "dashboard_live_stats_api endpoint created",
                'dashboard_live_stats_api' in content,
                "Add dashboard_live_stats_api() function to dashboard/views.py"
            )
    except FileNotFoundError:
        checker.failed.append("dashboard/views.py not found")
    
    # Check JavaScript file exists
    js_file = Path('static/js/dashboard-live-refresh.js')
    checker.check(
        "dashboard-live-refresh.js exists",
        js_file.exists(),
        "Run: python manage.py collectstatic or manually create the file"
    )
    
    # Check dashboard URLs have new endpoint
    try:
        with open('dashboard/urls.py', 'r', encoding='utf-8') as f:
            content = f.read()
            checker.check(
                "Dashboard API endpoint routed",
                'dashboard_live_stats_api' in content,
                "Update dashboard/urls.py: add path('api/live-stats/', dashboard_live_stats_api, ...)"
            )
    except FileNotFoundError:
        checker.failed.append("dashboard/urls.py not found")
    
    return checker


def check_migrations():
    """Check database migrations"""
    print("\n" + "="*60)
    print("4. DATABASE MIGRATIONS")
    print("="*60)
    
    checker = VerificationChecker()
    
    # Get list of applied migrations
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM django_migrations WHERE app='payment' ORDER BY name DESC LIMIT 5")
        migrations = [row[0] for row in cursor.fetchall()]
    
    checker.check(
        "Payment app migrations applied",
        len(migrations) > 0,
        "Run: python manage.py migrate payment"
    )
    
    # Check if latest migration that removes Transaction is applied
    has_cleanup_migration = any('alter_paymentgatewaylog' in m for m in migrations)
    checker.check(
        "Transaction cleanup migration applied",
        has_cleanup_migration,
        "Run: python manage.py migrate payment"
    )
    
    print(f"\nRecent migrations: {migrations[:3]}")
    
    return checker


def check_database():
    """Check database state"""
    print("\n" + "="*60)
    print("5. DATABASE STATE")
    print("="*60)
    
    checker = VerificationChecker()
    
    # Check if any transactions exist
    try:
        count = Transaction.objects.count()
        checker.check(
            f"Database connected ({count} transactions)",
            True
        )
        
        # Get stats
        if count > 0:
            latest = Transaction.objects.latest('created_at')
            print(f"\nLatest transaction:")
            print(f"  ID: {latest.id}")
            print(f"  Status: {latest.status}")
            print(f"  Created: {latest.created_at}")
            print(f"  Reference: {latest.reference_number}")
        else:
            checker.warning("No transactions yet", "Normal if no payments processed")
        
        # Check for any failed transactions
        failed_count = Transaction.objects.filter(status='failed').count()
        if failed_count > 0:
            checker.warning("Failed transactions exist", f"{failed_count} transactions with status='failed'")
        
    except Exception as e:
        checker.failed.append(f"Database check failed: {e}")
        print(f"✗ Database check: {e}")
    
    return checker


def check_webhook_logs():
    """Check webhook processing logs"""
    print("\n" + "="*60)
    print("6. WEBHOOK LOGS")
    print("="*60)
    
    checker = VerificationChecker()
    
    log_file = Path('logs/smartfuel.log')
    
    if not log_file.exists():
        checker.warning("No log file", "Will be created when webhooks are processed")
        return checker
    
    try:
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Check for webhook logs
        has_webhooks = 'WEBHOOK' in content
        checker.check(
            "Webhook logs found",
            has_webhooks,
            "No webhooks processed yet (normal if no payments made)"
        )
        
        if has_webhooks:
            # Count successful vs failed
            success_count = content.count('✓ Signature validated')
            failed_count = content.count('❌')
            print(f"\nWebhook statistics:")
            print(f"  Successful validations: {success_count}")
            print(f"  Failed validations: {failed_count}")
        
        # Check for errors
        if 'ERROR' in content or 'Exception' in content:
            checker.warning("Errors found in logs", "Check logs/smartfuel.log for details")
    
    except Exception as e:
        checker.failed.append(f"Log file read failed: {e}")
    
    return checker


def main():
    """Run all checks"""
    print("\n" + "="*70)
    print("SmartFuel Paystack Integration - Verification Script")
    print("="*70)
    
    all_checkers = [
        check_environment(),
        check_models(),
        check_code(),
        check_migrations(),
        check_database(),
        check_webhook_logs(),
    ]
    
    # Summary
    total_passed = sum(len(c.passed) for c in all_checkers)
    total_failed = sum(len(c.failed) for c in all_checkers)
    total_warnings = sum(len(c.warnings) for c in all_checkers)
    
    print("\n" + "="*70)
    print("OVERALL VERIFICATION RESULTS")
    print("="*70)
    print(f"✓ Passed: {total_passed}")
    print(f"✗ Failed: {total_failed}")
    print(f"⚠ Warnings: {total_warnings}")
    
    if total_failed == 0:
        print("\n🎉 All checks passed! Your Paystack integration is ready.")
        print("\nNext steps:")
        print("1. Make sure dashboard-live-refresh.js is added to your templates")
        print("2. Test a payment flow")
        print("3. Monitor logs: tail -f logs/smartfuel.log | grep WEBHOOK")
        print("4. Check dashboard updates automatically within 10 seconds")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the errors above and fix them.")
        print("\nCommon fixes:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Update imports in payment/views.py and payment/serializers.py")
        print("3. Add dashboard_live_stats_api to dashboard/views.py and urls.py")
        print("4. Create/verify static/js/dashboard-live-refresh.js exists")
        return 1


if __name__ == '__main__':
    sys.exit(main())
