from django.urls import path
from .views import (
    dashboard_home, user_profile, settings_view,
    admin_dashboard, manager_dashboard, attendant_dashboard, customer_dashboard,
    google_login, inventory_page, pumps_page, sales_page,
    customers_page, reports_page, price_history_page, payments_page,
    dashboard_live_signature, dashboard_live_stats_api,
)

urlpatterns = [
    # Single unified dashboard
    path("", dashboard_home, name="dashboard"),
    
    # Backward-compatible aliases that now resolve to the same dashboard page
    path("admin/", dashboard_home, name="admin_dashboard"),
    path("manager/", dashboard_home, name="manager_dashboard"),
    path("attendant/", dashboard_home, name="attendant_dashboard"),
    path("customer/", dashboard_home, name="customer_dashboard"),
    
    # User settings
    path("profile/", user_profile, name="profile"),
    path("settings/", settings_view, name="settings"),

    # Dashboard sections
    path("inventory/", inventory_page, name="dashboard_inventory"),
    path("pumps/", pumps_page, name="dashboard_pumps"),
    path("sales/", sales_page, name="dashboard_sales"),
    path("customers/", customers_page, name="dashboard_customers"),
    path("reports/", reports_page, name="dashboard_reports"),
    path("price-history/", price_history_page, name="dashboard_price_history"),
    path("payments/", payments_page, name="dashboard_payments"),
    path("live-signature/", dashboard_live_signature, name="dashboard_live_signature"),
    path("api/live-stats/", dashboard_live_stats_api, name="dashboard_live_stats_api"),
    
    # Google OAuth
    path("google/login/", google_login, name="google_oauth_login"),
]
