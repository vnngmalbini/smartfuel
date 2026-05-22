from __future__ import annotations

import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from station.models import Transaction

from .models import SMSDeliveryLog, PaymentAuditLog
from .services import normalize_phone_number


logger = logging.getLogger(__name__)

SMS_PROVIDER_LABELS = {
    'twilio': 'Twilio',
    'hubtel': 'Hubtel',
    'arkesel': 'Arkesel',
}


def _clean_text(value):
    return str(value).strip() if value not in (None, '') else ''


def record_payment_audit(event_type, message, *, transaction=None, payment=None, user=None, reference='', metadata=None):
    try:
        PaymentAuditLog.objects.create(
            transaction=transaction,
            payment=payment,
            user=user,
            event_type=event_type,
            reference=reference or getattr(transaction, 'reference_number', '') or getattr(payment, 'reference', '') or '',
            message=message,
            metadata=metadata or {},
        )
    except Exception:
        logger.exception('Failed to create payment audit log (%s)', event_type)


def build_payment_confirmation_message(transaction):
    payment = getattr(transaction, 'payment', None)

    customer_name = ''
    if payment and getattr(payment, 'customer_name', None):
        customer_name = payment.customer_name
    elif transaction.customer:
        customer_name = ' '.join(part for part in [transaction.customer.first_name, transaction.customer.last_name] if part).strip()

    customer_name = customer_name or 'Customer'
    amount_value = getattr(payment, 'amount', None) or getattr(transaction, 'total_amount', None) or Decimal('0')
    reference = getattr(payment, 'reference', None) or transaction.reference_number or transaction.transaction_id
    paid_at = getattr(payment, 'paid_at', None) or transaction.completed_at or transaction.created_at or timezone.now()
    paid_at_local = timezone.localtime(paid_at)

    return (
        f"FuelSync payment confirmed for {customer_name}. "
        f"Amount: GHS {Decimal(str(amount_value)):.2f}. "
        f"Ref: {reference}. "
        f"Date: {paid_at_local.strftime('%d %b %Y, %I:%M %p')}."
    )


def build_test_sms_message(provider_name=None):
    provider_label = SMS_PROVIDER_LABELS.get((provider_name or getattr(settings, 'SMS_PROVIDER', 'twilio')).lower(), 'SMS provider')
    return f"FuelSync test SMS: {provider_label} is configured and able to send messages."


def _fetch_json(url, *, headers=None, auth=None, timeout=8):
    response = requests.get(url, headers=headers or {}, auth=auth, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _provider_status_base(provider, *, credentials_ok, health_ok, balance=None, balance_currency='', balance_supported=False, message=''):
    provider_label = SMS_PROVIDER_LABELS.get(provider, provider.title())
    return {
        'provider': provider,
        'provider_label': provider_label,
        'credentials_ok': credentials_ok,
        'health_ok': health_ok,
        'balance_supported': balance_supported,
        'balance': balance,
        'balance_currency': balance_currency,
        'message': message,
        'status_class': 'success' if credentials_ok and health_ok else 'warning' if credentials_ok else 'danger',
    }


def get_sms_provider_status():
    provider = (getattr(settings, 'SMS_PROVIDER', 'twilio') or 'twilio').strip().lower()
    sms_enabled = bool(getattr(settings, 'SMS_ENABLED', False))

    if provider == 'twilio':
        account_sid = _clean_text(getattr(settings, 'TWILIO_ACCOUNT_SID', ''))
        auth_token = _clean_text(getattr(settings, 'TWILIO_AUTH_TOKEN', ''))
        from_number = _clean_text(getattr(settings, 'TWILIO_FROM_NUMBER', ''))
        credentials_ok = bool(account_sid and auth_token and from_number)
        balance = None
        balance_currency = ''
        message = 'Credentials incomplete'

        if credentials_ok:
            try:
                data = _fetch_json(
                    f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Balance.json',
                    auth=(account_sid, auth_token),
                )
                balance = data.get('balance')
                balance_currency = data.get('currency', '')
                message = 'Twilio account reachable'
                return {
                    **_provider_status_base('twilio', credentials_ok=True, health_ok=True, balance=balance, balance_currency=balance_currency, balance_supported=True, message=message),
                    'sms_enabled': sms_enabled,
                    'configured_fields': {
                        'account_sid': bool(account_sid),
                        'auth_token': bool(auth_token),
                        'from_number': bool(from_number),
                    },
                }
            except Exception as error:
                message = f'Twilio balance lookup failed: {error}'
                return {
                    **_provider_status_base('twilio', credentials_ok=True, health_ok=False, balance=balance, balance_currency=balance_currency, balance_supported=True, message=message),
                    'sms_enabled': sms_enabled,
                    'configured_fields': {
                        'account_sid': bool(account_sid),
                        'auth_token': bool(auth_token),
                        'from_number': bool(from_number),
                    },
                }

        return {
            **_provider_status_base('twilio', credentials_ok=False, health_ok=False, balance=balance, balance_currency=balance_currency, balance_supported=True, message=message),
            'sms_enabled': sms_enabled,
            'configured_fields': {
                'account_sid': bool(account_sid),
                'auth_token': bool(auth_token),
                'from_number': bool(from_number),
            },
        }

    if provider == 'hubtel':
        client_id = _clean_text(getattr(settings, 'HUBTEL_CLIENT_ID', ''))
        client_secret = _clean_text(getattr(settings, 'HUBTEL_CLIENT_SECRET', ''))
        sender_id = _clean_text(getattr(settings, 'SMS_SENDER_ID', ''))
        balance_url = _clean_text(getattr(settings, 'HUBTEL_BALANCE_URL', ''))
        credentials_ok = bool(client_id and client_secret and sender_id)
        balance = None
        message = 'Credentials incomplete'

        if credentials_ok and balance_url:
            try:
                data = _fetch_json(balance_url, auth=(client_id, client_secret))
                balance = data.get('balance') or data.get('credit') or data.get('remaining')
                message = 'Hubtel endpoint reachable'
                return {
                    **_provider_status_base('hubtel', credentials_ok=True, health_ok=True, balance=balance, balance_currency='', balance_supported=True, message=message),
                    'sms_enabled': sms_enabled,
                    'configured_fields': {
                        'client_id': bool(client_id),
                        'client_secret': bool(client_secret),
                        'sender_id': bool(sender_id),
                        'balance_url': bool(balance_url),
                    },
                }
            except Exception as error:
                message = f'Hubtel balance lookup failed: {error}'
                return {
                    **_provider_status_base('hubtel', credentials_ok=True, health_ok=False, balance=balance, balance_currency='', balance_supported=True, message=message),
                    'sms_enabled': sms_enabled,
                    'configured_fields': {
                        'client_id': bool(client_id),
                        'client_secret': bool(client_secret),
                        'sender_id': bool(sender_id),
                        'balance_url': bool(balance_url),
                    },
                }

        return {
            **_provider_status_base('hubtel', credentials_ok=credentials_ok, health_ok=credentials_ok, balance=balance, balance_currency='', balance_supported=bool(balance_url), message=message),
            'sms_enabled': sms_enabled,
            'configured_fields': {
                'client_id': bool(client_id),
                'client_secret': bool(client_secret),
                'sender_id': bool(sender_id),
                'balance_url': bool(balance_url),
            },
        }

    if provider == 'arkesel':
        api_key = _clean_text(getattr(settings, 'ARKESEL_API_KEY', ''))
        sender_id = _clean_text(getattr(settings, 'SMS_SENDER_ID', ''))
        balance_url = _clean_text(getattr(settings, 'ARKESEL_BALANCE_URL', ''))
        credentials_ok = bool(api_key and sender_id)
        balance = None
        message = 'Credentials incomplete'

        if credentials_ok and balance_url:
            try:
                response = requests.get(balance_url, headers={'api-key': api_key}, timeout=8)
                response.raise_for_status()
                data = response.json()
                balance = data.get('balance') or data.get('credit') or data.get('remaining')
                message = 'Arkesel endpoint reachable'
                return {
                    **_provider_status_base('arkesel', credentials_ok=True, health_ok=True, balance=balance, balance_currency='', balance_supported=True, message=message),
                    'sms_enabled': sms_enabled,
                    'configured_fields': {
                        'api_key': bool(api_key),
                        'sender_id': bool(sender_id),
                        'balance_url': bool(balance_url),
                    },
                }
            except Exception as error:
                message = f'Arkesel balance lookup failed: {error}'
                return {
                    **_provider_status_base('arkesel', credentials_ok=True, health_ok=False, balance=balance, balance_currency='', balance_supported=True, message=message),
                    'sms_enabled': sms_enabled,
                    'configured_fields': {
                        'api_key': bool(api_key),
                        'sender_id': bool(sender_id),
                        'balance_url': bool(balance_url),
                    },
                }

        return {
            **_provider_status_base('arkesel', credentials_ok=credentials_ok, health_ok=credentials_ok, balance=balance, balance_currency='', balance_supported=bool(balance_url), message=message),
            'sms_enabled': sms_enabled,
            'configured_fields': {
                'api_key': bool(api_key),
                'sender_id': bool(sender_id),
                'balance_url': bool(balance_url),
            },
        }

    return {
        **_provider_status_base(provider, credentials_ok=False, health_ok=False, message='Unsupported SMS provider'),
        'sms_enabled': sms_enabled,
        'configured_fields': {},
    }


def queue_sms_delivery(*, transaction=None, reference='', recipient_phone='', customer_name='', customer_email='', message='', purpose='payment_confirmation', provider=None, user=None, metadata=None):
    provider_name = (provider or getattr(settings, 'SMS_PROVIDER', 'twilio') or 'twilio').strip().lower()
    normalized_phone = normalize_phone_number(recipient_phone)
    payment_reference = reference or getattr(transaction, 'reference_number', '') or getattr(transaction, 'transaction_id', '')

    if not payment_reference:
        raise ValueError('A payment reference is required for SMS delivery logs.')
    if not normalized_phone:
        raise ValueError('A recipient phone number is required for SMS delivery.')
    if not message:
        raise ValueError('SMS message body is required.')

    defaults = {
        'transaction': transaction,
        'provider': provider_name,
        'recipient_phone': normalized_phone,
        'customer_name': _clean_text(customer_name),
        'customer_email': _clean_text(customer_email),
        'message': message,
        'status': 'queued',
        'provider_response': metadata or {},
    }

    try:
        with db_transaction.atomic():
            if transaction is not None:
                log, created = SMSDeliveryLog.objects.select_for_update().get_or_create(
                    transaction=transaction,
                    purpose=purpose,
                    defaults={**defaults, 'reference': payment_reference},
                )
            else:
                log, created = SMSDeliveryLog.objects.select_for_update().get_or_create(
                    reference=payment_reference,
                    purpose=purpose,
                    defaults=defaults,
                )

            if log.status == 'sent':
                record_payment_audit(
                    'sms_skipped',
                    'SMS confirmation skipped because it was already sent.',
                    transaction=transaction,
                    reference=payment_reference,
                    user=user,
                    metadata={'purpose': purpose, 'provider': provider_name},
                )
                return log, False

            if log.status in {'queued', 'processing', 'retrying'} and log.attempt_count > 0:
                return log, False

            log.provider = provider_name
            log.recipient_phone = normalized_phone
            log.customer_name = _clean_text(customer_name)
            log.customer_email = _clean_text(customer_email)
            log.message = message
            log.status = 'queued'
            log.error_message = ''
            log.provider_response = metadata or {}
            if created and not log.reference:
                log.reference = payment_reference
            log.save()

            record_payment_audit(
                'sms_queued',
                'SMS confirmation queued for delivery.',
                transaction=transaction,
                reference=payment_reference,
                user=user,
                metadata={'purpose': purpose, 'provider': provider_name, 'sms_delivery_log_id': log.id},
            )
    except Exception:
        logger.exception('Failed to queue SMS delivery for reference %s', payment_reference)
        raise

    try:
        from .tasks import process_sms_delivery

        process_sms_delivery.delay(log.id)
    except Exception as error:
        logger.warning('Celery queue unavailable for SMS %s, sending synchronously: %s', payment_reference, error)
        from .tasks import process_sms_delivery

        process_sms_delivery(log.id)

    return log, True