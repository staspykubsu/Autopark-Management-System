from django.contrib import admin
from django.utils import timezone
from .models import Car, Driver, Request, Trip, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email', 'phone']
    list_editable = ['role']
    
    actions = ['make_driver', 'make_dispatcher', 'make_manager']
    
    def make_driver(self, request, queryset):
        queryset.update(role='driver')
        self.message_user(request, f'{queryset.count()} пользователей назначены водителями')
    make_driver.short_description = 'Назначить водителями'
    
    def make_dispatcher(self, request, queryset):
        queryset.update(role='dispatcher')
        self.message_user(request, f'{queryset.count()} пользователей назначены диспетчерами')
    make_dispatcher.short_description = 'Назначить диспетчерами'
    
    def make_manager(self, request, queryset):
        queryset.update(role='manager')
        self.message_user(request, f'{queryset.count()} пользователей назначены руководством')
    make_manager.short_description = 'Назначить руководством'


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['brand_model', 'license_plate', 'status', 'mileage']
    list_filter = ['status']
    search_fields = ['brand_model', 'license_plate']
    list_editable = ['status', 'mileage']


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['name', 'license_number', 'phone', 'user']
    search_fields = ['name', 'license_number', 'user__username']
    list_filter = ['user__profile__role']


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ['driver', 'trip_date', 'status', 'created_at', 'processed_by']
    list_filter = ['status', 'trip_date']
    search_fields = ['driver__name', 'driver__user__username']
    list_editable = ['status']
    readonly_fields = ['created_at', 'processed_at']
    
    fieldsets = (
        ('Основная информация', {'fields': ('driver', 'trip_date', 'status')}),
        ('Обработка заявки', {'fields': ('rejection_reason', 'processed_by', 'processed_at'), 'classes': ('collapse',)}),
        ('Служебная информация', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )
    
    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            obj.processed_by = request.user
            obj.processed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['car', 'driver', 'departure_date', 'departure_mileage', 'return_date', 'return_mileage', 'distance_display', 'created_by']
    list_filter = ['car', 'driver', 'departure_date']
    search_fields = ['car__license_plate', 'driver__name']
    readonly_fields = ['departure_date', 'return_date', 'created_by', 'closed_by']
    
    fieldsets = (
        ('Основная информация', {'fields': ('car', 'driver', 'request')}),
        ('Выезд', {'fields': ('departure_date', 'departure_mileage', 'created_by')}),
        ('Возврат', {'fields': ('return_date', 'return_mileage', 'closed_by')}),
    )
    
    def distance_display(self, obj):
        dist = obj.distance()
        return f'{dist} км' if dist else '—'
    distance_display.short_description = 'Пройдено'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        elif 'return_mileage' in form.changed_data and obj.return_mileage:
            obj.closed_by = request.user
        super().save_model(request, obj, form, change)