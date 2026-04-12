"""Custom decorators for role-based access control"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()


def admin_required(view_func):
    """Only admins can access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.role == User.ROLE_ADMIN):
            messages.error(request, 'Access denied — Admin only.')
            return redirect('lands:land_list')
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_required(view_func):
    """Only land owners can access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('login')
        if not (request.user.is_owner or request.user.role == User.ROLE_OWNER):
            messages.error(request, 'Only land owners can access this page.')
            return redirect('lands:land_list')
        return view_func(request, *args, **kwargs)
    return wrapper


def customer_required(view_func):
    """Only customers can access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('login')
        if request.user.is_owner or request.user.role == User.ROLE_OWNER:
            messages.info(request, 'This feature is for customers. Switch to customer mode.')
            return redirect('lands:land_list')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_based_redirect(user):
    """Determine where user should be redirected based on role"""
    if user.is_staff or user.role == User.ROLE_ADMIN:
        return 'accounts:admin_portal'
    elif user.is_owner or user.role == User.ROLE_OWNER:
        return 'lands:owner_dashboard'
    else:
        return 'lands:customer_dashboard'
