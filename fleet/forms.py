from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Car, Driver, Request, Trip


class CarForm(forms.ModelForm):
    """Форма для автомобиля"""

    class Meta:
        model = Car
        fields = ['brand_model', 'license_plate', 'status', 'mileage']
        widgets = {
            'brand_model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Toyota Camry'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'А123БВ177'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'mileage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }


class DriverForm(forms.ModelForm):
    """Форма для водителя"""

    class Meta:
        model = Driver
        fields = ['name', 'license_number', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '7712345678'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
        }


class RequestForm(forms.ModelForm):
    """Форма для заявки"""

    class Meta:
        model = Request
        fields = ['requester_name', 'trip_date']
        widgets = {
            'requester_name': forms.TextInput(attrs={'class': 'form-control'}),
            'trip_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class RequestProcessForm(forms.ModelForm):
    """Форма для обработки заявки диспетчером"""

    class Meta:
        model = Request
        fields = ['status', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class TripStartForm(forms.ModelForm):
    """Форма для начала поездки (выдачи автомобиля)"""

    class Meta:
        model = Trip
        fields = ['car', 'driver', 'departure_mileage', 'request']
        widgets = {
            'car': forms.Select(attrs={'class': 'form-select'}),
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'departure_mileage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'request': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только свободные автомобили
        self.fields['car'].queryset = Car.objects.filter(status='free')
        self.fields['request'].required = False
        # По умолчанию текущее время
        self.initial['departure_date'] = timezone.now()

    def clean_car(self):
        car = self.cleaned_data['car']
        if car.status != 'free':
            raise ValidationError('Автомобиль недоступен для выдачи')
        return car


class TripEndForm(forms.ModelForm):
    """Форма для завершения поездки"""

    class Meta:
        model = Trip
        fields = ['return_mileage']
        widgets = {
            'return_mileage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }


class ReportFilterForm(forms.Form):
    """Форма для фильтрации отчетов по периоду"""

    date_from = forms.DateField(
        label='С',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        label='По',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )