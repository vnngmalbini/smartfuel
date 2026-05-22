from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentProvider, PaymentGatewayLog, CardToken, SMSDeliveryLog, PaymentAuditLog


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
	list_display = ['name', 'is_active', 'transaction_fee_percentage']
	list_editable = ['is_active', 'transaction_fee_percentage']
	fieldsets = (
		('Provider Information', {
			'fields': ('name', 'is_active', 'transaction_fee_percentage')
		}),
		('API Credentials', {
			'fields': ('api_key', 'api_secret'),
			'classes': ('collapse',),
			'description': 'Keep these credentials secure. Only accessible to administrators.'
		}),
	)

	def has_add_permission(self, request):
		# Only superusers can add providers
		return request.user.is_superuser

	def has_delete_permission(self, request, obj=None):
		# Only superusers can delete providers
		return request.user.is_superuser


@admin.register(PaymentGatewayLog)
class PaymentGatewayLogAdmin(admin.ModelAdmin):
	list_display = ['reference', 'provider', 'status_code', 'created_at']
	list_filter = ['provider', 'status_code', 'created_at']
	search_fields = ['reference', 'transaction__transaction_id']
	readonly_fields = ['created_at', 'request_data', 'response_data']
    
	fieldsets = (
		('Gateway Information', {
			'fields': ('reference', 'transaction', 'provider', 'status_code')
		}),
		('Request Data', {
			'fields': ('request_data',),
			'classes': ('collapse',)
		}),
		('Response Data', {
			'fields': ('response_data',),
			'classes': ('collapse',)
		}),
		('Error', {
			'fields': ('error_message',),
			'classes': ('collapse',)
		}),
		('System', {
			'fields': ('created_at',),
			'classes': ('collapse',)
		}),
	)
    
	def has_add_permission(self, request):
		return False
    
	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(CardToken)
class CardTokenAdmin(admin.ModelAdmin):
	list_display = ['card_display', 'user', 'phone', 'is_primary', 'expires_at']
	list_filter = ['is_primary', 'card_type', 'created_at']
	search_fields = ['phone', 'card_last4']
	readonly_fields = ['created_at', 'card_token']
    
	fieldsets = (
		('Card Information', {
			'fields': ('card_type', 'card_last4', 'expires_at')
		}),
		('Owner', {
			'fields': ('user', 'phone')
		}),
		('Settings', {
			'fields': ('is_primary',)
		}),
		('Security', {
			'fields': ('card_token',),
			'classes': ('collapse',),
			'description': 'Tokenized card reference for payment processing.'
		}),
		('System', {
			'fields': ('created_at',),
			'classes': ('collapse',)
		}),
	)
    
	def card_display(self, obj):
		return f"{obj.card_type} ••••{obj.card_last4}"
	card_display.short_description = 'Card'

	def has_add_permission(self, request):
		# Only superusers can add card tokens via admin
		return request.user.is_superuser

	def has_delete_permission(self, request, obj=None):
		# Only superusers can delete
		return request.user.is_superuser


@admin.register(SMSDeliveryLog)
class SMSDeliveryLogAdmin(admin.ModelAdmin):
	list_display = ['reference', 'purpose', 'provider', 'recipient_phone', 'customer_name', 'status', 'attempt_count', 'queued_at', 'sent_at']
	list_filter = ['purpose', 'provider', 'status', 'created_at', 'sent_at']
	search_fields = ['reference', 'recipient_phone', 'customer_name', 'customer_email', 'transaction__transaction_id']
	readonly_fields = ['queued_at', 'sent_at', 'created_at', 'updated_at', 'provider_response']

	fieldsets = (
		('Delivery', {
			'fields': ('transaction', 'purpose', 'provider', 'status', 'attempt_count', 'max_attempts')
		}),
		('Customer', {
			'fields': ('recipient_phone', 'customer_name', 'customer_email', 'reference')
		}),
		('Message', {
			'fields': ('message', 'provider_message_id', 'provider_response', 'error_message', 'next_retry_at')
		}),
		('System', {
			'fields': ('queued_at', 'sent_at', 'created_at', 'updated_at'),
			'classes': ('collapse',),
		}),
	)


@admin.register(PaymentAuditLog)
class PaymentAuditLogAdmin(admin.ModelAdmin):
	list_display = ['reference', 'event_type', 'user', 'created_at']
	list_filter = ['event_type', 'created_at']
	search_fields = ['reference', 'message', 'transaction__transaction_id', 'payment__reference', 'user__username']
	readonly_fields = ['created_at']

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return request.user.is_superuser
