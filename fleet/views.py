from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError

from .models import Car, Driver, Request, Trip, UserProfile
from .forms import (
    CarForm, DriverForm, RequestForm, RequestProcessForm,
    TripStartForm, TripEndForm, ReportFilterForm,
    UserRegistrationForm, UserProfileForm
)
from .mixins import DriverRequiredMixin, DispatcherRequiredMixin, ManagerRequiredMixin, StaffRequiredMixin


# ========== АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ ==========

class CustomLoginView(LoginView):
    """Страница входа"""
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        return reverse_lazy('home')
    
    def form_valid(self, form):
        messages.success(self.request, f'Добро пожаловать, {self.request.user.username}!')
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Выход из системы"""
    next_page = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'Вы вышли из системы')
        return super().dispatch(request, *args, **kwargs)


class RegisterView(CreateView):
    """Регистрация нового пользователя"""
    form_class = UserRegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, 'Регистрация успешна! Теперь вы можете войти в систему.')
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, TemplateView):
    """Профиль пользователя"""
    template_name = 'fleet/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        
        if self.request.user.profile.is_driver():
            try:
                context['driver'] = self.request.user.driver
                context['my_requests'] = Request.objects.filter(driver=self.request.user.driver).order_by('-created_at')
                context['my_trips'] = Trip.objects.filter(driver=self.request.user.driver).order_by('-departure_date')[:10]
            except Driver.DoesNotExist:
                context['driver'] = None
                context['my_requests'] = []
                context['my_trips'] = []
        
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Редактирование профиля"""
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'fleet/profile_edit.html'
    success_url = reverse_lazy('profile')
    
    def get_object(self, queryset=None):
        return self.request.user.profile
    
    def form_valid(self, form):
        messages.success(self.request, 'Профиль успешно обновлен')
        return super().form_valid(form)


# ========== УПРАВЛЕНИЕ РОЛЯМИ ==========

@method_decorator(staff_member_required, name='dispatch')
class ManageRolesView(ListView):
    """Управление ролями пользователей (только для администраторов)"""
    model = UserProfile
    template_name = 'fleet/manage_roles.html'
    context_object_name = 'profiles'
    
    def get_queryset(self):
        return UserProfile.objects.select_related('user').all().order_by('user__username')


@staff_member_required
def change_role(request, profile_id):
    """Изменение роли пользователя"""
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, id=profile_id)
        new_role = request.POST.get('role')
        
        if new_role in dict(UserProfile.ROLE_CHOICES):
            old_role = profile.get_role_display()
            profile.role = new_role
            profile.save()
            
            if new_role == 'driver':
                Driver.objects.get_or_create(
                    user=profile.user,
                    defaults={
                        'name': profile.user.get_full_name() or profile.user.username,
                        'phone': profile.phone
                    }
                )
            
            messages.success(request, f'Роль пользователя {profile.user.username} изменена с "{old_role}" на "{profile.get_role_display()}"')
        else:
            messages.error(request, 'Недопустимая роль')
    
    return redirect('manage_roles')


# ========== ГЛАВНАЯ ==========

class HomeView(LoginRequiredMixin, View):
    """Главная страница с дашбордом (содержимое зависит от роли)"""
    
    def get(self, request):
        user = request.user
        context = {}
        
        if user.profile.is_driver():
            # Водитель видит свои заявки и поездки
            try:
                driver = user.driver
                
                # Заявки
                context['my_requests'] = Request.objects.filter(driver=driver).order_by('-created_at')[:5]
                context['total_requests'] = Request.objects.filter(driver=driver).count()
                context['approved_requests'] = Request.objects.filter(driver=driver, status='approved').count()
                context['completed_requests'] = Request.objects.filter(driver=driver, status='completed').count()
                
                # Поездки
                context['active_trip'] = Trip.objects.filter(
                    driver=driver, 
                    departure_date__isnull=False,
                    return_date__isnull=True
                ).first()
                context['my_trips'] = Trip.objects.filter(
                    driver=driver,
                    return_date__isnull=False
                ).order_by('-departure_date')[:5]
                context['total_trips'] = Trip.objects.filter(driver=driver).count()
                
            except Driver.DoesNotExist:
                context['my_requests'] = []
                context['active_trip'] = None
                context['my_trips'] = []
                context['total_requests'] = 0
                context['approved_requests'] = 0
                context['completed_requests'] = 0
                context['total_trips'] = 0
        
        elif user.profile.is_dispatcher():
            # Диспетчер видит заявки и текущие поездки
            context['pending_requests'] = Request.objects.filter(status='new').count()
            context['active_trips_count'] = Trip.objects.filter(
                departure_date__isnull=False,
                return_date__isnull=True
            ).count()
            context['free_cars'] = Car.objects.filter(status='free').count()
            context['total_cars'] = Car.objects.count()
            context['recent_requests'] = Request.objects.filter(status='new').order_by('-created_at')[:10]
        
        elif user.profile.is_manager():
            # Руководство видит общую статистику
            context['total_cars'] = Car.objects.count()
            context['free_cars'] = Car.objects.filter(status='free').count()
            context['cars_in_trip'] = Car.objects.filter(status='trip').count()
            context['cars_in_repair'] = Car.objects.filter(status='repair').count()
            context['active_trips'] = Trip.objects.filter(
                departure_date__isnull=False,
                return_date__isnull=True
            ).count()
            context['total_drivers'] = Driver.objects.count()
            context['pending_requests'] = Request.objects.filter(status='new').count()
            context['recent_requests'] = Request.objects.filter(status='new').order_by('-created_at')[:10]
            
            # Статистика за текущий месяц
            today = timezone.now().date()
            month_start = today.replace(day=1)
            month_trips = Trip.objects.filter(
                departure_date__date__gte=month_start,
                return_date__isnull=False
            )
            
            total_distance = 0
            for trip in month_trips:
                if trip.distance():
                    total_distance += trip.distance()
            
            context['month_distance'] = total_distance
            context['month_trips_count'] = month_trips.count()
        
        return render(request, 'fleet/home.html', context)


# ========== АВТОМОБИЛИ ==========

class CarListView(LoginRequiredMixin, ListView):
    model = Car
    template_name = 'fleet/car_list.html'
    context_object_name = 'cars'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Car.STATUS_CHOICES
        context['current_filter'] = self.request.GET.get('status', '')
        context['can_edit'] = self.request.user.profile.is_manager()
        return context


class CarDetailView(LoginRequiredMixin, DetailView):
    model = Car
    template_name = 'fleet/car_detail.html'
    context_object_name = 'car'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        car = self.object
        context['trips'] = car.trips.all().order_by('-departure_date')
        
        trips = car.trips.filter(return_date__isnull=False)
        total_distance = 0
        completed_trips_count = 0
        
        for trip in trips:
            if trip.distance():
                total_distance += trip.distance()
                completed_trips_count += 1
        
        context['total_distance'] = total_distance
        context['avg_distance'] = total_distance / completed_trips_count if completed_trips_count > 0 else 0
        context['can_edit'] = self.request.user.profile.is_manager()
        
        return context


class CarCreateView(ManagerRequiredMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = 'fleet/car_form.html'
    success_url = reverse_lazy('car_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Автомобиль успешно добавлен')
        return super().form_valid(form)


class CarUpdateView(ManagerRequiredMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = 'fleet/car_form.html'
    success_url = reverse_lazy('car_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Данные автомобиля обновлены')
        return super().form_valid(form)


class CarDeleteView(ManagerRequiredMixin, DeleteView):
    model = Car
    template_name = 'fleet/car_confirm_delete.html'
    success_url = reverse_lazy('car_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Автомобиль удален')
        return super().delete(request, *args, **kwargs)


# ========== ВОДИТЕЛИ ==========

class DriverListView(LoginRequiredMixin, ListView):
    model = Driver
    template_name = 'fleet/driver_list.html'
    context_object_name = 'drivers'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.request.user.profile.is_manager()
        return context


class DriverDetailView(LoginRequiredMixin, DetailView):
    model = Driver
    template_name = 'fleet/driver_detail.html'
    context_object_name = 'driver'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['trips'] = self.object.trips.all().order_by('-departure_date')
        context['requests'] = self.object.requests.all().order_by('-created_at')
        return context


class DriverCreateView(ManagerRequiredMixin, CreateView):
    model = Driver
    form_class = DriverForm
    template_name = 'fleet/driver_form.html'
    success_url = reverse_lazy('driver_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Водитель успешно добавлен')
        return super().form_valid(form)


class DriverUpdateView(ManagerRequiredMixin, UpdateView):
    model = Driver
    form_class = DriverForm
    template_name = 'fleet/driver_form.html'
    success_url = reverse_lazy('driver_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Данные водителя обновлены')
        return super().form_valid(form)


class DriverDeleteView(ManagerRequiredMixin, DeleteView):
    model = Driver
    template_name = 'fleet/driver_confirm_delete.html'
    success_url = reverse_lazy('driver_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Водитель удален')
        return super().delete(request, *args, **kwargs)
    
# ========== ЗАЯВКИ ==========

class RequestListView(LoginRequiredMixin, ListView):
    model = Request
    template_name = 'fleet/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.profile.is_driver():
            try:
                queryset = queryset.filter(driver=user.driver)
            except Driver.DoesNotExist:
                queryset = queryset.none()
        
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_process'] = self.request.user.profile.is_dispatcher()
        context['status_choices'] = Request.STATUS_CHOICES
        context['current_filter'] = self.request.GET.get('status', '')
        return context


class RequestCreateView(DriverRequiredMixin, CreateView):
    """Создание заявки (только для водителей)"""
    model = Request
    form_class = RequestForm
    template_name = 'fleet/request_form.html'
    success_url = reverse_lazy('request_list')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            driver = request.user.driver
            if not driver.can_create_request():
                if driver.has_active_request():
                    messages.error(request, 'У вас уже есть активная заявка. Дождитесь её обработки.')
                elif driver.has_pending_trip():
                    messages.error(request, 'У вас есть одобренная заявка. Сначала совершите поездку.')
                elif driver.has_active_trip():
                    messages.error(request, 'У вас есть активная поездка. Завершите её перед созданием новой заявки.')
                return redirect('request_list')
        except Driver.DoesNotExist:
            messages.error(request, 'У вас нет профиля водителя')
            return redirect('profile')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        request_obj = form.save(commit=False)
        request_obj.driver = self.request.user.driver
        
        # Дополнительная проверка даты
        if request_obj.trip_date < timezone.localdate():
            messages.error(self.request, 'Нельзя создать заявку на прошедшую дату')
            return self.form_invalid(form)
        
        request_obj.save()
        messages.success(self.request, f'Заявка на {request_obj.trip_date.strftime("%d.%m.%Y")} успешно создана')
        return super().form_valid(form)


class RequestProcessView(DispatcherRequiredMixin, UpdateView):
    """Обработка заявки (только для диспетчеров)"""
    model = Request
    form_class = RequestProcessForm
    template_name = 'fleet/request_process.html'
    success_url = reverse_lazy('request_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_obj'] = self.object
        # Добавляем количество свободных автомобилей
        context['free_cars'] = Car.objects.filter(status='free').count()
        return context
    
    def form_valid(self, form):
        request_obj = form.save(commit=False)
        request_obj.processed_by = self.request.user
        request_obj.processed_at = timezone.now()
        request_obj.save()
        
        if request_obj.status == 'approved':
            # Создаем поездку БЕЗ автомобиля (водитель выберет сам)
            Trip.objects.create(
                request=request_obj,
                driver=request_obj.driver,
                created_by=self.request.user
            )
            messages.success(
                self.request, 
                f'Заявка №{request_obj.pk} одобрена. Поездка создана. '
                f'Водитель может начать поездку в разделе «Мои поездки».'
            )
        else:
            messages.warning(self.request, f'Заявка №{request_obj.pk} отклонена')
        
        return super().form_valid(form)


# ========== ПОЕЗДКИ ==========


class TripCreateView(DispatcherRequiredMixin, CreateView):
    """Начало поездки (только для диспетчеров)"""
    model = Trip
    form_class = TripStartForm
    template_name = 'fleet/trip_form.html'
    success_url = reverse_lazy('trip_list')
    
    def form_valid(self, form):
        trip = form.save(commit=False)
        trip.departure_date = timezone.now()
        trip.created_by = self.request.user
        
        if trip.car.status != 'free':
            messages.error(self.request, 'Автомобиль недоступен для выдачи')
            return self.form_invalid(form)
        
        trip.save()
        
        if trip.request and trip.request.status == 'approved':
            trip.request.status = 'approved'
            trip.request.save()
        
        trip.car.status = 'trip'
        trip.car.save()
        
        messages.success(self.request, f'Поездка начата. Автомобиль {trip.car} выдан водителю {trip.driver}')
        return redirect(self.success_url)


class TripCloseView(DispatcherRequiredMixin, UpdateView):
    """Завершение поездки (только для диспетчеров)"""
    model = Trip
    form_class = TripEndForm
    template_name = 'fleet/trip_close.html'
    success_url = reverse_lazy('trip_list')
    
    def get_queryset(self):
        return super().get_queryset().filter(return_date__isnull=True)
    
    def form_valid(self, form):
        trip = form.save(commit=False)
        
        if form.cleaned_data['return_mileage'] < trip.departure_mileage:
            messages.error(self.request, 'Пробег при возврате не может быть меньше пробега при выезде')
            return self.form_invalid(form)
        
        trip.return_date = timezone.now()
        trip.closed_by = self.request.user
        trip.save()
        
        distance = trip.return_mileage - trip.departure_mileage
        trip.car.mileage += distance
        trip.car.status = 'free'
        trip.car.save()
        
        messages.success(self.request, f'Поездка завершена. Пройдено {distance} км. Автомобиль {trip.car} свободен.')
        return redirect(self.success_url)


class TripDetailView(LoginRequiredMixin, DetailView):
    model = Trip
    template_name = 'fleet/trip_detail.html'
    context_object_name = 'trip'


# ========== ОТЧЕТЫ ==========

class ReportView(ManagerRequiredMixin, View):
    """Формирование отчета (только для руководства)"""
    template_name = 'fleet/report.html'
    
    def get(self, request):
        form = ReportFilterForm(initial={
            'date_from': timezone.now().replace(day=1).date(),
            'date_to': timezone.now().date(),
        })
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = ReportFilterForm(request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            
            car_report = Trip.objects.filter(
                departure_date__date__gte=date_from,
                departure_date__date__lte=date_to,
                return_date__isnull=False
            ).values('car__brand_model', 'car__license_plate').annotate(
                total_distance=Sum('return_mileage') - Sum('departure_mileage'),
                trips_count=Count('id')
            ).order_by('-total_distance')
            
            driver_report = Trip.objects.filter(
                departure_date__date__gte=date_from,
                departure_date__date__lte=date_to,
                return_date__isnull=False
            ).values('driver__name').annotate(
                total_distance=Sum('return_mileage') - Sum('departure_mileage'),
                trips_count=Count('id')
            ).order_by('-total_distance')
            
            context = {
                'form': form,
                'car_report': car_report,
                'driver_report': driver_report,
                'date_from': date_from,
                'date_to': date_to,
            }
            return render(request, self.template_name, context)
        
        return render(request, self.template_name, {'form': form})
    
class MyTripsView(LoginRequiredMixin, ListView):
    """Мои поездки (для водителя)"""
    model = Trip
    template_name = 'fleet/my_trips.html'
    context_object_name = 'trips'
    
    def get_queryset(self):
        try:
            return Trip.objects.filter(driver=self.request.user.driver).order_by('-departure_date')
        except Driver.DoesNotExist:
            return Trip.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            driver = self.request.user.driver
            context['active_trip'] = driver.trips.filter(return_date__isnull=True, departure_date__isnull=False).first()
            context['waiting_trip'] = driver.trips.filter(departure_date__isnull=True).first()
            context['can_create_request'] = driver.can_create_request()
        except Driver.DoesNotExist:
            pass
        return context

class TripStartView(DriverRequiredMixin, View):
    """Начало поездки водителем"""
    
    def get(self, request, trip_id):
        try:
            trip = Trip.objects.get(id=trip_id, driver=request.user.driver)
        except Trip.DoesNotExist:
            messages.error(request, 'Поездка не найдена')
            return redirect('my_trips')
        
        if not trip.is_waiting():
            messages.error(request, 'Эту поездку нельзя начать')
            return redirect('my_trips')
        
        can_start, message = trip.can_be_started()
        if not can_start:
            messages.error(request, message)
            return redirect('my_trips')
        
        form = TripStartForm()
        return render(request, 'fleet/trip_start.html', {
            'form': form,
            'trip': trip,
            'trip_date': trip.request.trip_date if trip.request else None
        })
    
    def post(self, request, trip_id):
        try:
            trip = Trip.objects.get(id=trip_id, driver=request.user.driver)
        except Trip.DoesNotExist:
            messages.error(request, 'Поездка не найдена')
            return redirect('my_trips')
        
        if not trip.is_waiting():
            messages.error(request, 'Эту поездку нельзя начать')
            return redirect('my_trips')
        
        can_start, message = trip.can_be_started()
        if not can_start:
            messages.error(request, message)
            return redirect('my_trips')
        
        form = TripStartForm(request.POST)
        if form.is_valid():
            car = form.cleaned_data['car']
            
            try:
                trip.start_trip(car)
                trip.created_by = request.user
                trip.save()
                messages.success(request, f'Поездка начата. Автомобиль {car.license_plate}')
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'fleet/trip_start.html', {
                    'form': form,
                    'trip': trip,
                    'trip_date': trip.request.trip_date if trip.request else None
                })
            
            return redirect('my_trips')
        
        return render(request, 'fleet/trip_start.html', {
            'form': form,
            'trip': trip,
            'trip_date': trip.request.trip_date if trip.request else None
        })

class TripEndView(DriverRequiredMixin, View):
    """Завершение поездки водителем"""
    
    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id, driver=request.user.driver)
        
        if not trip.is_active():
            messages.error(request, 'Эту поездку нельзя завершить')
            return redirect('my_trips')
        
        form = TripEndForm()
        return render(request, 'fleet/trip_end.html', {'form': form, 'trip': trip})
    
    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id, driver=request.user.driver)
        
        if not trip.is_active():
            messages.error(request, 'Эту поездку нельзя завершить')
            return redirect('my_trips')
        
        form = TripEndForm(request.POST)
        if form.is_valid():
            return_mileage = form.cleaned_data['return_mileage']
            
            if return_mileage < trip.departure_mileage:
                messages.error(request, 'Пробег при возврате не может быть меньше пробега при выезде')
                return render(request, 'fleet/trip_end.html', {'form': form, 'trip': trip})
            
            trip.end_trip(return_mileage)
            trip.closed_by = request.user
            trip.save()
            
            messages.success(request, f'Поездка завершена. Пройдено {trip.distance()} км')
            return redirect('my_trips')
        
        return render(request, 'fleet/trip_end.html', {'form': form, 'trip': trip})

class TripListView(LoginRequiredMixin, ListView):
    model = Trip
    template_name = 'fleet/trip_list.html'
    context_object_name = 'trips'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().exclude(departure_date__isnull=True)
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(return_date__isnull=True)
        elif status == 'completed':
            queryset = queryset.filter(return_date__isnull=False)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(car__license_plate__icontains=search) |
                Q(driver__name__icontains=search)
            )
        
        return queryset.select_related('car', 'driver')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_trips_count'] = Trip.objects.filter(return_date__isnull=True, departure_date__isnull=False).count()
        return context