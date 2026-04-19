from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .models import Car, Driver, Request, Trip
from .forms import (
    CarForm, DriverForm, RequestForm, RequestProcessForm,
    TripStartForm, TripEndForm, ReportFilterForm
)


class HomeView(View):
    """Главная страница с дашбордом"""

    def get(self, request):
        context = {
            'total_cars': Car.objects.count(),
            'free_cars': Car.objects.filter(status='free').count(),
            'active_trips': Trip.objects.filter(return_date__isnull=True).count(),
            'total_drivers': Driver.objects.count(),
            'pending_requests': Request.objects.filter(status='new').count(),
            'recent_trips': Trip.objects.all().order_by('-departure_date')[:10],
        }
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
        return context


class CarDetailView(LoginRequiredMixin, DetailView):
    model = Car
    template_name = 'fleet/car_detail.html'
    context_object_name = 'car'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['trips'] = self.object.trips.all().order_by('-departure_date')
        return context


class CarCreateView(LoginRequiredMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = 'fleet/car_form.html'
    success_url = reverse_lazy('car_list')

    def form_valid(self, form):
        messages.success(self.request, 'Автомобиль успешно добавлен')
        return super().form_valid(form)


class CarUpdateView(LoginRequiredMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = 'fleet/car_form.html'
    success_url = reverse_lazy('car_list')

    def form_valid(self, form):
        messages.success(self.request, 'Данные автомобиля обновлены')
        return super().form_valid(form)


class CarDeleteView(LoginRequiredMixin, DeleteView):
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


class DriverCreateView(LoginRequiredMixin, CreateView):
    model = Driver
    form_class = DriverForm
    template_name = 'fleet/driver_form.html'
    success_url = reverse_lazy('driver_list')

    def form_valid(self, form):
        messages.success(self.request, 'Водитель успешно добавлен')
        return super().form_valid(form)


class DriverUpdateView(LoginRequiredMixin, UpdateView):
    model = Driver
    form_class = DriverForm
    template_name = 'fleet/driver_form.html'
    success_url = reverse_lazy('driver_list')


class DriverDeleteView(LoginRequiredMixin, DeleteView):
    model = Driver
    template_name = 'fleet/driver_confirm_delete.html'
    success_url = reverse_lazy('driver_list')


# ========== ЗАЯВКИ ==========

class RequestListView(LoginRequiredMixin, ListView):
    model = Request
    template_name = 'fleet/request_list.html'
    context_object_name = 'requests'


class RequestCreateView(LoginRequiredMixin, CreateView):
    model = Request
    form_class = RequestForm
    template_name = 'fleet/request_form.html'
    success_url = reverse_lazy('request_list')

    def form_valid(self, form):
        messages.success(self.request, 'Заявка создана')
        return super().form_valid(form)


class RequestProcessView(LoginRequiredMixin, UpdateView):
    """Обработка заявки диспетчером (одобрить/отклонить)"""
    model = Request
    form_class = RequestProcessForm
    template_name = 'fleet/request_process.html'
    success_url = reverse_lazy('request_list')

    def form_valid(self, form):
        status = form.cleaned_data['status']
        if status == 'approved':
            messages.success(self.request, 'Заявка одобрена')
        else:
            messages.warning(self.request, 'Заявка отклонена')
        return super().form_valid(form)


# ========== ПОЕЗДКИ ==========

class TripListView(LoginRequiredMixin, ListView):
    model = Trip
    template_name = 'fleet/trip_list.html'
    context_object_name = 'trips'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        # Фильтр по статусу
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(return_date__isnull=True)
        elif status == 'completed':
            queryset = queryset.filter(return_date__isnull=False)

        # Поиск
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(car__license_plate__icontains=search) |
                Q(driver__name__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_trips_count'] = Trip.objects.filter(return_date__isnull=True).count()
        return context


class TripCreateView(LoginRequiredMixin, CreateView):
    """Начало поездки (выдача автомобиля)"""
    model = Trip
    form_class = TripStartForm
    template_name = 'fleet/trip_form.html'
    success_url = reverse_lazy('trip_list')

    def form_valid(self, form):
        trip = form.save(commit=False)
        trip.departure_date = timezone.now()

        # Проверяем, что автомобиль свободен
        if trip.car.status != 'free':
            messages.error(self.request, 'Автомобиль недоступен для выдачи')
            return self.form_invalid(form)

        trip.save()

        # Меняем статус автомобиля на "В рейсе"
        trip.car.status = 'trip'
        trip.car.save()

        messages.success(self.request, f'Поездка начата. Автомобиль {trip.car} выдан водителю {trip.driver}')
        return redirect(self.success_url)


class TripCloseView(LoginRequiredMixin, UpdateView):
    """Завершение поездки (возврат автомобиля)"""
    model = Trip
    form_class = TripEndForm
    template_name = 'fleet/trip_close.html'
    success_url = reverse_lazy('trip_list')

    def get_queryset(self):
        # Можно закрыть только активные поездки
        return super().get_queryset().filter(return_date__isnull=True)

    def form_valid(self, form):
        trip = form.save(commit=False)

        # Проверка, что пробег при возврате больше пробега при выезде
        if form.cleaned_data['return_mileage'] < trip.departure_mileage:
            messages.error(self.request, 'Пробег при возврате не может быть меньше пробега при выезде')
            return self.form_invalid(form)

        trip.return_date = timezone.now()
        trip.save()

        # Обновляем пробег автомобиля и меняем статус
        distance = trip.return_mileage - trip.departure_mileage
        trip.car.mileage += distance
        trip.car.status = 'free'
        trip.car.save()

        messages.success(
            self.request,
            f'Поездка завершена. Пройдено {distance} км. '
            f'Автомобиль {trip.car} свободен.'
        )
        return redirect(self.success_url)


class TripDetailView(LoginRequiredMixin, DetailView):
    model = Trip
    template_name = 'fleet/trip_detail.html'
    context_object_name = 'trip'


# ========== ОТЧЕТЫ ==========

class ReportView(LoginRequiredMixin, View):
    """Формирование отчета по пробегу за период"""

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

            # Отчет по автомобилям
            car_report = Trip.objects.filter(
                departure_date__date__gte=date_from,
                departure_date__date__lte=date_to,
                return_date__isnull=False
            ).values(
                'car__brand_model',
                'car__license_plate'
            ).annotate(
                total_distance=Sum('return_mileage') - Sum('departure_mileage'),
                trips_count=Count('id')
            ).order_by('-total_distance')

            # Отчет по водителям
            driver_report = Trip.objects.filter(
                departure_date__date__gte=date_from,
                departure_date__date__lte=date_to,
                return_date__isnull=False
            ).values(
                'driver__name'
            ).annotate(
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