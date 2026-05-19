#!/usr/bin/env python
"""
Create or update the Google SocialApplication from environment variables.

Usage (PowerShell):

# set env vars for current session
$env:GOOGLE_CLIENT_ID = 'your-client-id'
$env:GOOGLE_CLIENT_SECRET = 'your-client-secret'
& 'venv\Scripts\python.exe' scripts\create_social_app.py

Or on cmd / bash:

GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... python scripts/create_social_app.py

This script expects `SITE_ID=1` to exist (we created it earlier).
"""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        import django
        django.setup()
    except Exception as exc:
        print('Error initializing Django:', exc)
        sys.exit(1)

    from django.contrib.sites.models import Site
    from allauth.socialaccount.models import SocialApp

    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        print('Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET environment variables.')
        print('Set them and re-run this script.')
        sys.exit(1)

    try:
        site = Site.objects.get(pk=1)
    except Site.DoesNotExist:
        site = Site.objects.create(id=1, domain='localhost:8000', name='localhost')
        print('Created Site id=1 -> localhost:8000')

    app, created = SocialApp.objects.update_or_create(
        provider='google',
        defaults={
            'name': 'SmartFuel Google',
            'client_id': client_id,
            'secret': client_secret,
        }
    )
    app.sites.set([site])
    app.save()

    if created:
        print('SocialApp (google) created and attached to site.')
    else:
        print('SocialApp (google) updated and attached to site.')

    print('Done.')
