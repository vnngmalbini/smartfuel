from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect, render

from .models import UserProfile


def get_user_role(user):
    if not user.is_authenticated:
        return None

    profile = UserProfile.objects.filter(user=user).only('role').first()
    if profile:
        return profile.role

    if user.is_superuser:
        return 'admin'

    return 'customer'


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)

            if role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            messages.error(request, "You do not have permission to access that area.")
            # Return permission denied instead of redirecting to prevent redirect loops
            return render(request, 'permission_denied.html', status=403)

        return wrapped

    return decorator