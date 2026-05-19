from django.contrib import admin
from .models import UserProfile
from .models import DashboardDailySummary


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ['user', 'phone', 'role', 'dark_mode', 'email_notifications']
	list_filter = ['role', 'dark_mode', 'email_notifications', 'created_at']
	search_fields = ['user__username', 'user__email', 'phone']
	readonly_fields = ['created_at', 'updated_at']
    
	fieldsets = (
		('User Account', {
			'fields': ('user',)
		}),
		('Personal Information', {
			'fields': ('phone', 'profile_picture', 'bio', 'role')
		}),
		('Location', {
			'fields': ('country', 'city', 'address')
		}),
		('Preferences', {
			'fields': ('dark_mode', 'email_notifications', 'sms_notifications')
		}),
		('System', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)

@admin.register(DashboardDailySummary)
class DashboardDailySummaryAdmin(admin.ModelAdmin):
	list_display = ['summary_date', 'today_revenue', 'transaction_count', 'total_fuel_dispensed', 'pending_payments', 'last_transaction_reference', 'updated_at']
	readonly_fields = ['updated_at']
	ordering = ['-summary_date']


# Declutter admin: unregister rarely-used or third-party models that
# administrators don't need to edit frequently. Keep `User` and
# `UserProfile` visible for user management.
try:
	from allauth.account.models import EmailAddress
except Exception:
	EmailAddress = None

try:
	from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
except Exception:
	SocialAccount = SocialApp = SocialToken = None

try:
	from rest_framework.authtoken.models import Token
except Exception:
	Token = None

try:
	from django.contrib.sites.models import Site
except Exception:
	Site = None

for model in (EmailAddress, SocialAccount, SocialApp, SocialToken, Token, Site):
	if model is None:
		continue
	try:
		admin.site.unregister(model)
	except Exception:
		# model not registered or other unregister issue; ignore
		pass
