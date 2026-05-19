from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from PIL import Image
import os

User = get_user_model()

class UserProfile(models.Model):
    """Extended user profile with preferences"""
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('attendant', 'Attendant'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_profile')
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='customer')
    bio = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True, null=True)
    
    # Preferences
    dark_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username


class DashboardDailySummary(models.Model):
    """Persisted live dashboard totals for a given day."""

    summary_date = models.DateField(unique=True)
    today_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transaction_count = models.PositiveIntegerField(default=0)
    total_fuel_dispensed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_payments = models.PositiveIntegerField(default=0)
    last_transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    last_transaction_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-summary_date']

    def __str__(self):
        return f"Dashboard summary for {self.summary_date}"


def refresh_dashboard_summary(target_date=None):
    """Rebuild the stored dashboard totals for a date."""
    from station.models import Transaction, FuelType

    summary_date = target_date or timezone.localdate()

    completed_txns = Transaction.objects.filter(
        created_at__date=summary_date,
        status='completed',
    ).filter(
        Q(fuel_type__isnull=True) | ~Q(fuel_type__name__iexact='lpg')
    )

    today_revenue = completed_txns.aggregate(total=Sum('total_amount'))['total'] or 0
    transaction_count = completed_txns.count()
    total_fuel_dispensed = completed_txns.aggregate(total=Sum('liters_dispensed'))['total'] or 0

    pending_payments = Transaction.objects.filter(status='pending').exclude(
        fuel_type__name__iexact='lpg'
    ).count()

    latest_txn = completed_txns.order_by('-created_at').first()

    summary, _ = DashboardDailySummary.objects.update_or_create(
        summary_date=summary_date,
        defaults={
            'today_revenue': today_revenue,
            'transaction_count': transaction_count,
            'total_fuel_dispensed': total_fuel_dispensed,
            'pending_payments': pending_payments,
            'last_transaction_reference': getattr(latest_txn, 'reference_number', None) or '',
            'last_transaction_at': getattr(latest_txn, 'created_at', None),
        },
    )
    return summary


def refresh_daily_sales_report(target_date=None):
    """Rebuild the persisted daily sales report for a given date."""
    from station.models import Transaction, DailySalesReport

    report_date = target_date or timezone.localdate()

    completed_txns = Transaction.objects.filter(
        created_at__date=report_date,
        status='completed',
    ).filter(
        Q(fuel_type__isnull=True) | ~Q(fuel_type__name__iexact='lpg')
    )

    total_transactions = completed_txns.count()
    total_liters_sold = completed_txns.aggregate(total=Sum('liters_dispensed'))['total'] or 0
    total_revenue = completed_txns.aggregate(total=Sum('total_amount'))['total'] or 0

    fuel_totals = completed_txns.values('fuel_type__name').annotate(total=Sum('liters_dispensed'))
    petrol_sold = 0
    diesel_sold = 0
    lpg_sold = 0
    for item in fuel_totals:
        fuel_name = item.get('fuel_type__name')
        total = item.get('total') or 0
        if fuel_name == 'petrol':
            petrol_sold = total
        elif fuel_name == 'diesel':
            diesel_sold = total
        elif fuel_name == 'lpg':
            lpg_sold = total

    total_expenses = 0
    profit = total_revenue - total_expenses

    report, _ = DailySalesReport.objects.update_or_create(
        date=report_date,
        defaults={
            'total_transactions': total_transactions,
            'total_liters_sold': total_liters_sold,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'profit': profit,
            'petrol_sold': petrol_sold,
            'diesel_sold': diesel_sold,
            'lpg_sold': lpg_sold,
        },
    )
    return report


@receiver(post_save, sender=UserProfile)
def process_profile_picture(sender, instance, **kwargs):
    """Process and optimize uploaded profile picture"""
    if instance.profile_picture:
        try:
            # Open the image
            img = Image.open(instance.profile_picture.path)
            
            # Check if already processed (if size is already 300x300, skip)
            if img.size == (300, 300):
                return
            
            # Crop to square
            width, height = img.size
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            right = left + size
            bottom = top + size
            img = img.crop((left, top, right, bottom))
            
            # Resize to 300x300px
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Save the processed image
            img.save(instance.profile_picture.path, quality=95, optimize=True)
            
        except (IOError, OSError, AttributeError):
            # If there's an error processing the image, just continue
            pass


@receiver(post_save)
@receiver(post_delete)
def update_dashboard_summary_on_transaction_change(sender, instance, **kwargs):
    """Refresh the persisted dashboard summary whenever a sale changes."""
    try:
        from station.models import Transaction
    except Exception:
        return

    if sender is not Transaction:
        return

    changed_date = getattr(instance, 'created_at', None)
    if changed_date is not None:
        changed_date = timezone.localdate(changed_date)
    refresh_dashboard_summary(changed_date)
    refresh_daily_sales_report(changed_date)
