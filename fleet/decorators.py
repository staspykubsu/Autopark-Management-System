from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages


def role_required(allowed_roles):
    """Декоратор для проверки роли пользователя"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            try:
                user_role = request.user.profile.role
                if user_role in allowed_roles:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, 'У вас нет доступа к этой странице')
                    return redirect('home')
            except AttributeError:
                messages.error(request, 'Профиль пользователя не найден')
                return redirect('home')
        return _wrapped_view
    return decorator


def driver_required(view_func):
    return role_required(['driver'])(view_func)


def dispatcher_required(view_func):
    return role_required(['dispatcher'])(view_func)


def manager_required(view_func):
    return role_required(['manager'])(view_func)


def staff_required(view_func):
    return role_required(['dispatcher', 'manager'])(view_func)