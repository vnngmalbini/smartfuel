from datetime import timedelta
from collections import defaultdict
import logging

from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Sum, Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal

logger = logging.getLogger(__name__)

from .forms import (
    AvatarUploadForm,
    PhoneAuthenticationForm,
    PhoneSignupForm,
    ProfilePreferencesForm,
    ProfilePictureForm,
    UserProfileForm,
)
from .permissions import get_user_role, role_required
from .models import UserProfile
from .models import DashboardDailySummary, refresh_dashboard_summary, refresh_daily_sales_report
from station.models import (
    FuelInventory, Notification, Pump, Transaction, 
    FuelType, Staff, Receipt, Customer, DailySalesReport, Payment, FuelPriceHistory
)


def _build_dashboard_live_signature():
    """Build a compact signature that changes whenever dashboard KPIs change."""
    today = timezone.localdate()

    completed_txns = Transaction.objects.filter(
        created_at__date=today,
        status='completed',
    ).exclude(
        fuel_type__name__iexact='lpg'
    )

    today_revenue = completed_txns.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    transaction_count = completed_txns.count()
    pending_payments = Transaction.objects.filter(status='pending').exclude(fuel_type__name__iexact='lpg').count()

    low_stock_count = 0
    for inventory in FuelInventory.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg'):
        if inventory.is_low_stock():
            low_stock_count += 1

    latest_txn = completed_txns.order_by('-created_at').values('transaction_id', 'created_at').first()
    latest_txn_id = latest_txn['transaction_id'] if latest_txn else ''
    latest_ts = latest_txn['created_at'].isoformat() if latest_txn and latest_txn['created_at'] else ''

    return f"{transaction_count}|{float(today_revenue):.2f}|{pending_payments}|{low_stock_count}|{latest_txn_id}|{latest_ts}"


class PhoneLoginView(LoginView):
    template_name = "login.html"
    authentication_form = PhoneAuthenticationForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Always send authenticated users to the unified dashboard."""
        return '/dashboard/'


@login_required
@role_required('admin', 'manager', 'attendant')
def dashboard_home(request):
    today = timezone.localdate()

    period_transactions = Transaction.objects.filter(
        created_at__date=today,
        status='completed',
    ).filter(_exclude_lpg_filter())

    today_revenue = period_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    transaction_count = period_transactions.count()
    total_fuel_dispensed = period_transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0
    pending_payments = Transaction.objects.filter(status='pending').filter(_exclude_lpg_filter()).count()

    yesterday = today - timedelta(days=1)
    yesterday_transactions = Transaction.objects.filter(
        created_at__date=yesterday,
        status='completed',
    ).filter(_exclude_lpg_filter())
    yesterday_revenue = yesterday_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    yesterday_transaction_count = yesterday_transactions.count()
    yesterday_fuel_dispensed = yesterday_transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0
    
    fuel_inventories = FuelInventory.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg')
    low_stock_count = sum(1 for inv in fuel_inventories if inv.is_low_stock())
    total_fuel_types = fuel_inventories.count()

    fuel_details = []
    for inventory in fuel_inventories:
        fuel_type_name = inventory.fuel_type.get_name_display()
        fuel_details.append({
            'name': fuel_type_name,
            'quantity': inventory.quantity_liters,
            'max_capacity': inventory.max_capacity,
            'percentage': (inventory.quantity_liters / inventory.max_capacity * 100) if inventory.max_capacity > 0 else 0,
            'is_low_stock': inventory.is_low_stock(),
            'status_badge': 'Low Stock' if inventory.is_low_stock() else 'OK'
        })

    recent_transactions = period_transactions.select_related(
        'pump', 'fuel_type', 'customer', 'staff'
    ).order_by('-created_at')[:5]
    
    transactions_data = []
    for txn in recent_transactions:
        transactions_data.append({
            'transaction_id': txn.transaction_id,
            'customer_name': txn.customer.first_name + ' ' + txn.customer.last_name if txn.customer else 'N/A',
            'fuel_type': txn.fuel_type.get_name_display() if txn.fuel_type else 'N/A',
            'amount': txn.total_amount,
            'status': txn.status.capitalize(),
            'time': txn.created_at.strftime('%I:%M %p') if txn.created_at else 'N/A',
        })

    recent_payments = Payment.objects.select_related('transaction', 'transaction__customer').order_by('-created_at')[:5]
    payment_data = []
    for payment in recent_payments:
        transaction = payment.transaction
        payment_data.append({
            'reference': payment.reference,
            'customer_name': transaction.customer.first_name + ' ' + transaction.customer.last_name if transaction.customer else 'N/A',
            'amount': payment.amount,
            'status': payment.status.capitalize(),
            'method': payment.payment_method.replace('_', ' ').title(),
            'time': payment.created_at.strftime('%I:%M %p') if payment.created_at else 'N/A',
        })

    pumps = Pump.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg')
    pump_data = []
    for pump in pumps:
        pump_data.append({
            'pump_number': pump.pump_number,
            'fuel_type': pump.fuel_type.get_name_display(),
            'status': pump.status.capitalize(),
            'status_class': pump.status.lower(),
            'total_liters_dispensed': pump.total_liters_dispensed,
            'total_revenue': pump.total_revenue,
        })

    active_pumps = pumps.filter(status='operational').count()
    total_pumps = pumps.count()

    completed_customers = period_transactions.exclude(customer__isnull=True).values('customer').distinct().count()
    average_customer_spend = float(today_revenue) / completed_customers if completed_customers else 0

    daily_transactions = list(period_transactions.order_by('created_at'))
    revenue_buckets = []
    for start_hour in range(6, 22, 2):
        revenue_buckets.append({'label': f'{start_hour:02d}:00', 'revenue': 0.0, 'transactions': 0, 'liters': 0.0})

    for txn in daily_transactions:
        bucket_index = min(max((txn.created_at.hour - 6) // 2, 0), len(revenue_buckets) - 1)
        revenue_buckets[bucket_index]['revenue'] += float(txn.total_amount)
        revenue_buckets[bucket_index]['transactions'] += 1
        revenue_buckets[bucket_index]['liters'] += float(txn.liters_dispensed)

    revenue_trend_labels = [bucket['label'] for bucket in revenue_buckets]
    revenue_trend_values = [bucket['revenue'] for bucket in revenue_buckets]
    transaction_trend_values = [bucket['transactions'] for bucket in revenue_buckets]
    fuel_dispensed_trend_values = [bucket['liters'] for bucket in revenue_buckets]

    fuel_type_totals = {}
    weekly_labels = []
    weekly_totals = []
    for txn in daily_transactions:
        fuel_name = txn.fuel_type.get_name_display()
        fuel_type_totals[fuel_name] = fuel_type_totals.get(fuel_name, 0) + float(txn.total_amount)
        weekly_labels.append(txn.created_at.strftime('%a'))
        weekly_totals.append(float(txn.total_amount))

    if not weekly_labels:
        weekly_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_totals = [0, 0, 0, 0, 0, 0, 0]

    if not fuel_type_totals:
        fuel_type_totals = {
            'Petrol': 0,
            'Diesel': 0,
        }

    most_purchased_fuel = max(fuel_type_totals.items(), key=lambda item: item[1])[0]

    def percent_change(current, previous):
        if previous in (None, 0):
            return 100.0 if current else 0.0
        return ((float(current) - float(previous)) / float(previous)) * 100

    revenue_change = percent_change(today_revenue, yesterday_revenue)
    transaction_change = percent_change(transaction_count, yesterday_transaction_count)
    fuel_change = percent_change(total_fuel_dispensed, yesterday_fuel_dispensed)
    low_stock_rate = (low_stock_count / total_fuel_types * 100) if total_fuel_types else 0
    active_pump_rate = (active_pumps / total_pumps * 100) if total_pumps else 0
    pending_payment_rate = (pending_payments / (transaction_count + pending_payments) * 100) if (transaction_count + pending_payments) else 0

    monthly_revenue = []
    current_year = today.year
    current_month = today.month
    for index in range(5, -1, -1):
        month_number = current_month - index
        year = current_year
        while month_number <= 0:
            month_number += 12
            year -= 1
        while month_number > 12:
            month_number -= 12
            year += 1

        month_start = timezone.make_aware(timezone.datetime(year, month_number, 1))
        if month_number == 12:
            next_month = timezone.make_aware(timezone.datetime(year + 1, 1, 1))
        else:
            next_month = timezone.make_aware(timezone.datetime(year, month_number + 1, 1))

        month_total = Transaction.objects.filter(
            created_at__gte=month_start,
            created_at__lt=next_month,
            status='completed',
        ).exclude(
            fuel_type__name__iexact='lpg'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        monthly_revenue.append({
            'label': timezone.datetime(year, month_number, 1).strftime('%b'),
            'value': float(month_total),
        })

    peak_hours = []
    for hour in range(6, 22, 2):
        hour_total = period_transactions.filter(created_at__hour=hour).count()
        peak_hours.append({'label': f'{hour:02d}:00', 'value': hour_total})

    current_time = timezone.localtime(timezone.now())
    display_name_source = request.user.get_short_name() or request.user.first_name or request.user.username
    display_name = str(display_name_source).replace('.', ' ').replace('_', ' ')
    greeting_hour = current_time.hour
    greeting = 'morning' if greeting_hour < 12 else 'afternoon' if greeting_hour < 18 else 'evening'

    sparkline_map = {
        'revenue': revenue_trend_values[-8:] or [0],
        'transactions': transaction_trend_values[-8:] or [0],
        'fuel_dispensed': fuel_dispensed_trend_values[-8:] or [0],
        'low_stock': [low_stock_count for _ in range(8)] or [0],
        'active_pumps': [active_pumps for _ in range(8)] or [0],
        'pending_payments': [pending_payments for _ in range(8)] or [0],
    }

    kpi_cards = [
        {
            'label': 'Revenue Today',
            'value': f'GH₵{float(today_revenue):.0f}',
            'trend': revenue_change,
            'trend_label': 'vs yesterday',
            'icon': 'cash-coin',
            'tone': 'blue',
            'sparkline_key': 'revenue',
        },
        {
            'label': 'Transactions',
            'value': f'{transaction_count}',
            'trend': transaction_change,
            'trend_label': 'vs yesterday',
            'icon': 'receipt-cutoff',
            'tone': 'green',
            'sparkline_key': 'transactions',
        },
        {
            'label': 'Fuel Dispensed',
            'value': f'{float(total_fuel_dispensed):.2f} L',
            'trend': fuel_change,
            'trend_label': 'vs yesterday',
            'icon': 'droplet-half',
            'tone': 'orange',
            'sparkline_key': 'fuel_dispensed',
        },
        {
            'label': 'Low Stock Alerts',
            'value': f'{low_stock_count}',
            'trend': low_stock_rate,
            'trend_label': 'inventory at risk',
            'icon': 'exclamation-triangle',
            'tone': 'red',
            'sparkline_key': 'low_stock',
        },
        {
            'label': 'Active Pumps',
            'value': f'{active_pumps}',
            'trend': active_pump_rate,
            'trend_label': 'uptime rate',
            'icon': 'fuel-pump',
            'tone': 'navy',
            'sparkline_key': 'active_pumps',
        },
        {
            'label': 'Pending Payments',
            'value': f'{pending_payments}',
            'trend': pending_payment_rate,
            'trend_label': 'of transactions',
            'icon': 'wallet2',
            'tone': 'slate',
            'sparkline_key': 'pending_payments',
        },
    ]

    pump_status_summary = defaultdict(int)
    for pump in pump_data:
        pump_status_summary[pump['status_class']] += 1

    notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:5]
    notification_data = []
    for notif in notifications:
        notification_data.append({
            'type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'type_badge': notif.notification_type.replace('_', ' ').title()
        })

    recent_alerts = notification_data[:3]
    
    has_dashboard_data = any([
        transaction_count,
        total_fuel_dispensed,
        low_stock_count,
        pending_payments,
        active_pumps,
        total_fuel_types,
        total_pumps,
        bool(fuel_details),
        bool(transactions_data),
        bool(notification_data),
        bool(peak_hours and any(item['value'] for item in peak_hours)),
    ])
    
    context = {
        'today_revenue': today_revenue,
        'transaction_count': transaction_count,
        'total_fuel_dispensed': total_fuel_dispensed,
        'low_stock_count': low_stock_count,
        'pending_payments': pending_payments,
        'active_pumps': active_pumps,
        'average_customer_spend': average_customer_spend,
        'most_purchased_fuel': most_purchased_fuel,
        'current_time': current_time,
        'greeting': greeting,
        'display_name': display_name,
        'fuel_details': fuel_details,
        'recent_transactions': transactions_data,
        'recent_payments': payment_data,
        'pump_data': pump_data,
        'notifications': notification_data,
        'recent_alerts': recent_alerts,
        'kpi_cards': kpi_cards,
        'sparkline_map': sparkline_map,
        'pump_status_summary': dict(pump_status_summary),
        'has_dashboard_data': has_dashboard_data,
        'revenue_trend_labels': revenue_trend_labels,
        'revenue_trend_values': revenue_trend_values,
        'transaction_trend_values': transaction_trend_values,
        'fuel_dispensed_trend_values': fuel_dispensed_trend_values,
        'fuel_type_labels': list(fuel_type_totals.keys()),
        'fuel_type_values': list(fuel_type_totals.values()),
        'weekly_labels': weekly_labels,
        'weekly_totals': weekly_totals,
        'monthly_revenue': monthly_revenue,
        'peak_hours': peak_hours,
        'live_signature': _build_dashboard_live_signature(),
    }
    
    return render(request, "dashboard_saas.html", context)


@login_required
@role_required('admin', 'manager', 'attendant')
def dashboard_live_signature(request):
    """Return a lightweight signature used by the dashboard for live-refresh checks."""
    return JsonResponse({
        'signature': _build_dashboard_live_signature(),
        'server_time': timezone.localtime(timezone.now()).isoformat(),
    })


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return render(request, "logout.html")

def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    
    form = PhoneSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        role = get_user_role(user)
        role_label = role.title() if role else "User"
        messages.success(request, f"{role_label} account created successfully. Please log in to continue.")
        return redirect("login")
    
    return render(request, "signup.html", {"form": form})


@login_required
def user_profile(request):
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = ProfilePictureForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        user_form = UserProfileForm(instance=request.user)
        profile_form = ProfilePictureForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, "profile.html", context)


@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    display_name = (request.user.get_full_name() or '').strip()

    if not display_name:
        customer = getattr(request.user, 'customer_profile', None)
        if customer:
            display_name = f"{customer.first_name} {customer.last_name}".strip()

    if not display_name:
        display_name = str(request.user.username).replace('.', ' ').replace('_', ' ')

    if request.method == "POST":
        if "save_preferences" in request.POST:
            avatar_form = AvatarUploadForm(instance=profile)
            preferences_form = ProfilePreferencesForm(request.POST, instance=profile)
            if preferences_form.is_valid():
                preferences_form.save()
                messages.success(request, "Preferences updated successfully.")
                return redirect("settings")
            messages.error(request, "Please review your preference settings and try again.")
        else:
            avatar_form = AvatarUploadForm(request.POST, request.FILES, instance=profile)
            preferences_form = ProfilePreferencesForm(instance=profile)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, "Profile picture updated successfully.")
                return redirect("settings")
            messages.error(request, "Please select a valid image file.")
    else:
        avatar_form = AvatarUploadForm(instance=profile)
        preferences_form = ProfilePreferencesForm(instance=profile)

    return render(
        request,
        "settings.html",
        {
            "profile": profile,
            "avatar_form": avatar_form,
            "preferences_form": preferences_form,
            "display_name": display_name,
        },
    )


@login_required
@role_required('admin', 'manager', 'attendant')
def inventory_page(request):
    fuel_inventories = FuelInventory.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg')
    low_stock_count = sum(1 for item in fuel_inventories if item.is_low_stock())

    inventory_rows = []
    for item in fuel_inventories:
        percentage = (item.quantity_liters / item.max_capacity * 100) if item.max_capacity else 0
        inventory_rows.append({
            'fuel_name': item.fuel_type.get_name_display(),
            'quantity_liters': item.quantity_liters,
            'max_capacity': item.max_capacity,
            'percentage': percentage,
            'is_low_stock': item.is_low_stock(),
        })

    context = {
        'page_title': 'Inventory',
        'inventory_rows': inventory_rows,
        'total_fuel_types': len(inventory_rows),
        'low_stock_count': low_stock_count,
    }
    return render(request, 'dashboard_inventory.html', context)


@login_required
@role_required('admin', 'manager', 'attendant')
def pumps_page(request):
    pumps = Pump.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg').order_by('pump_number')
    context = {
        'page_title': 'Pumps',
        'pumps': pumps,
        'operational_count': pumps.filter(status='operational').count(),
        'maintenance_count': pumps.filter(status='maintenance').count(),
        'offline_count': pumps.filter(status='offline').count(),
    }
    return render(request, 'dashboard_pumps.html', context)


@login_required
@role_required('admin', 'manager', 'attendant')
def sales_page(request):
    sales = Transaction.objects.select_related('fuel_type', 'pump', 'customer', 'staff').filter(
        status='completed'
    ).exclude(
        fuel_type__name__iexact='lpg'
    ).order_by('-created_at')[:50]

    totals = Transaction.objects.filter(status='completed').exclude(fuel_type__name__iexact='lpg').aggregate(
        total_revenue=Sum('total_amount'),
        total_liters=Sum('liters_dispensed'),
        total_count=Count('id'),
    )

    context = {
        'page_title': 'Sales',
        'sales': sales,
        'total_revenue': totals.get('total_revenue') or 0,
        'total_liters': totals.get('total_liters') or 0,
        'total_count': totals.get('total_count') or 0,
    }
    return render(request, 'dashboard_sales.html', context)


@login_required
@role_required('admin', 'manager', 'attendant')
def customers_page(request):
    customers = Customer.objects.all().order_by('-created_at')[:100]
    context = {
        'page_title': 'Customers',
        'customers': customers,
        'total_customers': Customer.objects.count(),
    }
    return render(request, 'dashboard_customers.html', context)


@login_required
@role_required('admin', 'manager', 'attendant')
def reports_page(request):
    today = timezone.localdate()
    refresh_daily_sales_report(today)
    reports = DailySalesReport.objects.all().order_by('-date')[:30]
    start_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    today_sales = Transaction.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt, status='completed').exclude(fuel_type__name__iexact='lpg')

    context = {
        'page_title': 'Reports',
        'reports': reports,
        'today_revenue': today_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'today_liters': today_sales.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0,
        'today_transactions': today_sales.count(),
    }
    return render(request, 'dashboard_reports.html', context)


@login_required
@role_required('admin', 'manager', 'attendant')
def price_history_page(request):
    fuel_types = FuelType.objects.exclude(name__iexact='lpg').order_by('id')
    price_history_rows = []

    for fuel_type in fuel_types:
        current_rate = fuel_type.current_price
        price_history_rows.append({
            'id': fuel_type.id,
            'diesel': current_rate if fuel_type.name == 'diesel' else None,
            'petrol': current_rate if fuel_type.name == 'petrol' else None,
            'current_rate': current_rate,
            'created_at': fuel_type.price_updated_at,
        })

    context = {
        'page_title': 'Price History',
        'price_history_rows': price_history_rows,
    }
    return render(request, 'dashboard_price_history.html', context)


@login_required
@role_required('admin', 'manager', 'attendant')
def payments_page(request):
    payments_qs = Payment.objects.select_related('transaction').all().order_by('-created_at')
    context = {
        'page_title': 'Payments',
        'payments': payments_qs[:50],
        'pending_count': payments_qs.filter(status='pending').count(),
        'completed_count': payments_qs.filter(status='completed').count(),
        'failed_count': payments_qs.filter(status='failed').count(),
    }
    return render(request, 'dashboard_payments.html', context)


# ==================== ROLE-BASED DASHBOARDS ====================

@login_required
@role_required('admin')
def admin_dashboard(request):
    """Admin Dashboard - System-wide view and management"""
    today = timezone.localdate()
    start_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    # Revenue metrics
    today_transactions = Transaction.objects.filter(
        created_at__gte=start_dt,
        created_at__lte=end_dt,
        status='completed'
    ).filter(_exclude_lpg_filter())
    today_revenue = today_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # All time metrics
    total_revenue = Transaction.objects.filter(status='completed').filter(_exclude_lpg_filter()).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_transactions = Transaction.objects.filter(status='completed').filter(_exclude_lpg_filter()).count()
    total_customers = Customer.objects.count()
    total_staff = Staff.objects.filter(is_active=True).count()
    
    # Fuel inventory
    fuel_inventories = FuelInventory.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg')
    low_stock_fuels = [inv for inv in fuel_inventories if inv.is_low_stock()]
    
    # Pump status
    pumps = Pump.objects.exclude(fuel_type__name__iexact='lpg')
    pump_status = {
        'operational': pumps.filter(status='operational').count(),
        'maintenance': pumps.filter(status='maintenance').count(),
        'offline': pumps.filter(status='offline').count(),
    }
    
    # Recent transactions for admin
    recent_transactions = today_transactions.select_related('pump', 'fuel_type', 'customer', 'staff').order_by('-created_at')[:10]
    
    # Fuel prices
    fuel_types = FuelType.objects.exclude(name__iexact='lpg')
    
    context = {
        'page_title': 'Admin Dashboard',
        'today_revenue': today_revenue,
        'total_revenue': total_revenue,
        'total_transactions': total_transactions,
        'total_customers': total_customers,
        'total_staff': total_staff,
        'low_stock_count': len(low_stock_fuels),
        'low_stock_fuels': low_stock_fuels,
        'fuel_inventories': fuel_inventories,
        'pump_status': pump_status,
        'recent_transactions': recent_transactions,
        'fuel_types': fuel_types,
        'active_pumps': pump_status['operational'],
    }
    
    return render(request, 'dashboard_admin.html', context)


@login_required
@role_required('manager')
def manager_dashboard(request):
    """Manager Dashboard - Daily operations and reporting"""
    today = timezone.localdate()
    start_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    # Today's metrics
    today_transactions = Transaction.objects.filter(
        created_at__date=today,
        status='completed'
    ).exclude(
        fuel_type__name__iexact='lpg'
    )
    today_revenue = today_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    today_liters = today_transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0
    today_count = today_transactions.count()
    
    # Weekly metrics
    week_start = today - timedelta(days=today.weekday())
    week_transactions = Transaction.objects.filter(
        created_at__date__gte=week_start,
        status='completed'
    ).exclude(
        fuel_type__name__iexact='lpg'
    )
    week_revenue = week_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Monthly metrics
    month_start = today.replace(day=1)
    month_transactions = Transaction.objects.filter(
        created_at__date__gte=month_start,
        status='completed'
    ).exclude(
        fuel_type__name__iexact='lpg'
    )
    month_revenue = month_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Real-time fuel stock
    fuel_inventories = FuelInventory.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg')
    
    # Attendant performance
    attendants = Staff.objects.filter(role__name='attendant', is_active=True).select_related('user')
    attendant_performance = []
    for attendant in attendants:
        txn_count = Transaction.objects.filter(staff=attendant, status='completed').exclude(fuel_type__name__iexact='lpg').count()
        txn_revenue = Transaction.objects.filter(staff=attendant, status='completed').exclude(fuel_type__name__iexact='lpg').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        attendant_performance.append({
            'name': attendant.user.get_full_name(),
            'transactions': txn_count,
            'revenue': txn_revenue,
        })
    
    # Pump status
    pumps = Pump.objects.exclude(fuel_type__name__iexact='lpg')
    pump_data = []
    for pump in pumps:
        pump_data.append({
            'pump_number': pump.pump_number,
            'fuel_type': pump.fuel_type.get_name_display(),
            'status': pump.status,
            'total_dispensed': pump.total_liters_dispensed,
        })
    
    context = {
        'page_title': 'Manager Dashboard',
        'today_revenue': today_revenue,
        'today_liters': today_liters,
        'today_transactions': today_count,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'fuel_inventories': fuel_inventories,
        'attendant_performance': attendant_performance,
        'pump_data': pump_data,
    }
    
    return render(request, 'dashboard_manager.html', context)


@login_required
@role_required('attendant')
def attendant_dashboard(request):
    """Attendant Dashboard - Fuel sales and transactions"""
    today = timezone.localdate()
    start_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end_dt = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    # Get current staff
    try:
        staff = request.user.staff_profile
    except Staff.DoesNotExist:
        staff = None
    
    # Today's sales for this attendant
    today_transactions = Transaction.objects.filter(
        staff=staff,
        created_at__date=today,
        status='completed'
    ).exclude(fuel_type__name__iexact='lpg') if staff else Transaction.objects.none()
    
    today_revenue = today_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    today_liters = today_transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0
    today_count = today_transactions.count()
    
    # Shift performance
    total_revenue = Transaction.objects.filter(staff=staff, status='completed').exclude(fuel_type__name__iexact='lpg').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_transactions = Transaction.objects.filter(staff=staff, status='completed').exclude(fuel_type__name__iexact='lpg').count()
    
    # Available pumps
    pumps = Pump.objects.filter(status='operational').exclude(fuel_type__name__iexact='lpg')
    
    # Fuel types for selection
    fuel_types = FuelType.objects.exclude(name__iexact='lpg')
    
    # Recent transactions
    recent_txns = today_transactions.select_related('fuel_type', 'customer', 'pump').order_by('-created_at')[:5]
    
    context = {
        'page_title': 'Attendant Dashboard',
        'staff': staff,
        'today_revenue': today_revenue,
        'today_liters': today_liters,
        'today_transactions': today_count,
        'total_revenue': total_revenue,
        'total_transactions': total_transactions,
        'pumps': pumps,
        'fuel_types': fuel_types,
        'recent_transactions': recent_txns,
    }
    
    return render(request, 'dashboard_attendant.html', context)


@login_required
@role_required('customer')
def customer_dashboard(request):
    """Customer Dashboard - Personal purchases and rewards"""
    try:
        customer = request.user.customer_profile
    except Customer.DoesNotExist:
        customer = None
    
    # Customer's transactions
    transactions = Transaction.objects.filter(
        customer=customer,
        status='completed'
    ).exclude(fuel_type__name__iexact='lpg').select_related('fuel_type', 'pump') if customer else Transaction.objects.none()
    
    total_spent = transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_liters = transactions.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or 0
    total_visits = transactions.count()
    average_spent_per_visit = (total_spent / total_visits) if total_visits else 0
    points_to_next_tier = max(500 - (customer.loyalty_points if customer else 0), 0)
    
    # Recent transactions
    recent_txns = transactions.order_by('-created_at')[:5]
    
    # Loyalty info
    loyalty_points = customer.loyalty_points if customer else 0
    
    context = {
        'page_title': 'Customer Dashboard',
        'customer': customer,
        'total_spent': total_spent,
        'total_liters': total_liters,
        'total_visits': total_visits,
        'loyalty_points': loyalty_points,
        'average_spent_per_visit': average_spent_per_visit,
        'points_to_next_tier': points_to_next_tier,
        'recent_transactions': recent_txns,
    }
    
    return render(request, 'dashboard_customer.html', context)


@login_required
@role_required('admin', 'manager', 'attendant')
def dashboard_live_stats_api(request):
    """
    API endpoint for live dashboard statistics.
    Returns today's KPIs as JSON for auto-refresh functionality.
    """
    today = timezone.localdate()
    
    try:
        summary = DashboardDailySummary.objects.filter(summary_date=today).first()
        if summary is None:
            summary = refresh_dashboard_summary(today)

        # Get today's completed transactions
        completed_txns = Transaction.objects.filter(
            created_at__date=today,
            status='completed',
        ).filter(_exclude_lpg_filter())
        
        # Use persisted KPIs from the database summary row so dashboard updates
        # immediately when a sale is committed.
        today_revenue = summary.today_revenue if summary else (completed_txns.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'))
        transaction_count = summary.transaction_count if summary else completed_txns.count()
        total_fuel_dispensed = summary.total_fuel_dispensed if summary else (completed_txns.aggregate(Sum('liters_dispensed'))['liters_dispensed__sum'] or Decimal('0'))
        pending_payments = summary.pending_payments if summary else Transaction.objects.filter(status='pending').filter(_exclude_lpg_filter()).count()
        
        # Get recent transactions
        recent_transactions = completed_txns.select_related(
            'pump', 'fuel_type', 'customer', 'staff'
        ).order_by('-created_at')[:5]
        
        recent_txns_data = []
        for txn in recent_transactions:
            recent_txns_data.append({
                'transaction_id': txn.transaction_id,
                'customer_name': txn.customer.first_name + ' ' + txn.customer.last_name if txn.customer else 'N/A',
                'fuel_type': txn.fuel_type.get_name_display() if txn.fuel_type else 'N/A',
                'amount': float(txn.total_amount),
                'status': txn.status.capitalize(),
                'time': txn.created_at.strftime('%I:%M %p') if txn.created_at else 'N/A',
            })
        
        # Get fuel inventory status
        fuel_inventories = FuelInventory.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg')
        low_stock_count = sum(1 for inv in fuel_inventories if inv.is_low_stock())
        
        # Get pump status
        pumps = Pump.objects.select_related('fuel_type').exclude(fuel_type__name__iexact='lpg')
        active_pumps = pumps.filter(status='operational').count()
        total_pumps = pumps.count()
        
        return JsonResponse({
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'kpis': {
                'today_revenue': float(today_revenue),
                'transaction_count': transaction_count,
                'total_fuel_dispensed': float(total_fuel_dispensed),
                'pending_payments': pending_payments,
                'low_stock_count': low_stock_count,
                'active_pumps': active_pumps,
                'total_pumps': total_pumps,
            },
            'recent_transactions': recent_txns_data,
            'signature': _build_dashboard_live_signature(),  # Used to detect changes
        })
    except Exception as e:
        logger.exception(f"Error in dashboard_live_stats_api: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e),
        }, status=500)


def google_login(request):
    """
    Redirect to Google OAuth endpoint.
    This proxies to the allauth Google login route so the app uses one
    canonical callback path.
    """
    try:
        return redirect('/accounts/google/login/')
    except Exception:
        messages.error(request, "Google login is not configured. Please contact the administrator.")
        return redirect('login')

def _exclude_lpg_filter():
    """Returns Q filter that includes non-LPG fuel types and NULL fuel types (e.g., Paystack payments)"""
    return Q(fuel_type__isnull=True) | ~Q(fuel_type__name__iexact='lpg')
