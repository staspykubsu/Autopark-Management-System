from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Car, Driver, Request, Trip, UserProfile


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя (роль по умолчанию - driver)"""
    
    email = forms.EmailField(required=True, label='Email')
    first_name = forms.CharField(max_length=30, required=True, label='Имя')
    last_name = forms.CharField(max_length=30, required=True, label='Фамилия')
    phone = forms.CharField(max_length=15, required=False, label='Телефон')
    license_number = forms.CharField(
        max_length=20, 
        required=False, 
        label='Номер водительского удостоверения',
        help_text='Только для водителей'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {'username': forms.TextInput(attrs={'class': 'form-control'})}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            user.profile.role = 'driver'
            user.profile.phone = self.cleaned_data.get('phone', '')
            user.profile.save()
            
            license_number = self.cleaned_data.get('license_number', '')
            Driver.objects.create(
                user=user,
                name=f"{user.last_name} {user.first_name}",
                license_number=license_number if license_number else '',
                phone=self.cleaned_data.get('phone', '')
            )
        return user


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label='Имя')
    last_name = forms.CharField(max_length=30, required=True, label='Фамилия')
    email = forms.EmailField(required=True, label='Email')
    
    class Meta:
        model = UserProfile
        fields = ['phone']
        widgets = {'phone': forms.TextInput(attrs={'class': 'form-control'})}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.email = self.cleaned_data['email']
            profile.user.save()
            profile.save()
        return profile


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['brand_model', 'license_plate', 'status', 'mileage']
        widgets = {
            'brand_model': forms.TextInput(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'mileage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['name', 'license_number', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['trip_date']
        widgets = {
            'trip_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trip_date'].widget.attrs['min'] = timezone.localdate().isoformat()
    
    def clean_trip_date(self):
        trip_date = self.cleaned_data.get('trip_date')
        today = timezone.localdate()
        
        if trip_date < today:
            raise forms.ValidationError('Нельзя создать заявку на прошедшую дату. Выберите сегодняшнюю или будущую дату.')
        
        return trip_date


class RequestProcessForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['status', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class TripStartForm(forms.Form):
    """Форма для начала поездки водителем (только выбор автомобиля)"""
    car = forms.ModelChoiceField(
        queryset=Car.objects.filter(status='free'),
        label='Автомобиль',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        self.request_obj = kwargs.pop('request_obj', None)
        super().__init__(*args, **kwargs)
    
    def clean_car(self):
        car = self.cleaned_data['car']
        if car.status != 'free':
            raise forms.ValidationError('Автомобиль недоступен')
        return car


class TripEndForm(forms.Form):
    """Форма для завершения поездки водителем"""
    return_mileage = forms.IntegerField(
        label='Пробег при возврате',
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


class ReportFilterForm(forms.Form):
    date_from = forms.DateField(label='С', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_to = forms.DateField(label='По', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))