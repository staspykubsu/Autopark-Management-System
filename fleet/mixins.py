from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Миксин для проверки роли пользователя"""
    allowed_roles = []
    
    def test_func(self):
        try:
            return self.request.user.profile.role in self.allowed_roles
        except AttributeError:
            return False
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'У вас нет доступа к этой странице')
        return redirect('home')


class DriverRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['driver']


class DispatcherRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['dispatcher']


class ManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['manager']


class StaffRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['dispatcher', 'manager']