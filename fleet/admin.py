from django.contrib import admin
from .models import Car, Driver, Request, Trip


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['brand_model', 'license_plate', 'status', 'mileage']
    list_filter = ['status']
    search_fields = ['brand_model', 'license_plate']
    list_editable = ['status', 'mileage']


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['name', 'license_number', 'phone']
    search_fields = ['name', 'license_number']


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ['requester_name', 'trip_date', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['requester_name']
    list_editable = ['status']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        'car', 'driver', 'departure_date', 'departure_mileage',
        'return_date', 'return_mileage', 'distance_display'
    ]
    list_filter = ['car', 'driver']
    search_fields = ['car__license_plate', 'driver__name']
    readonly_fields = ['departure_date', 'return_date']

    def distance_display(self, obj):
        dist = obj.distance()
        return f'{dist} км' if dist else '—'
    distance_display.short_description = 'Пройдено'