"""
Google OAuth Configuration for SmartFuel
"""
import os
from django.conf import settings

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:8000/accounts/google/login/callback/')

# For development/testing - create test credentials
if not GOOGLE_CLIENT_ID:
    GOOGLE_CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID_HERE'
if not GOOGLE_CLIENT_SECRET:
    GOOGLE_CLIENT_SECRET = 'YOUR_GOOGLE_CLIENT_SECRET_HERE'

GOOGLE_OAUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USER_INFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
