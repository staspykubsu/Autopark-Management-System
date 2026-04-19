#!/usr/bin/env python
"""Скрипт для инициализации тестовых данных"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autopark.settings')
django.setup()

from django.contrib.auth.models import User
from fleet.models import UserProfile, Driver, Car

print("=" * 60)
print("Создание тестовых данных для Автопарк «Ветерок»")
print("=" * 60)

# Создаем пользователей с разными ролями
users_data = [
    {'username': 'driver1', 'password': 'driver123', 'email': 'driver1@example.com', 
     'first_name': 'Иван', 'last_name': 'Иванов', 'role': 'driver', 
     'phone': '+79001112233', 'license': '77АА111111'},
    {'username': 'driver2', 'password': 'driver123', 'email': 'driver2@example.com', 
     'first_name': 'Петр', 'last_name': 'Петров', 'role': 'driver', 
     'phone': '+79002223344', 'license': '77АА222222'},
    {'username': 'dispatcher', 'password': 'disp123', 'email': 'disp@example.com', 
     'first_name': 'Анна', 'last_name': 'Сидорова', 'role': 'dispatcher', 
     'phone': '+79003334455', 'license': None},
    {'username': 'manager', 'password': 'manager123', 'email': 'manager@example.com', 
     'first_name': 'Сергей', 'last_name': 'Кузнецов', 'role': 'manager', 
     'phone': '+79004445566', 'license': None},
]

for data in users_data:
    user, created = User.objects.get_or_create(username=data['username'])
    if created:
        user.email = data['email']
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.set_password(data['password'])
        user.save()
        
        user.profile.role = data['role']
        user.profile.phone = data['phone']
        user.profile.save()
        
        if data['role'] == 'driver' and data['license']:
            Driver.objects.create(
                user=user,
                name=f"{data['last_name']} {data['first_name']}",
                license_number=data['license'],
                phone=data['phone']
            )
        print(f"✅ Пользователь: {data['username']} ({data['role']}) - создан")
    else:
        print(f"ℹ️ Пользователь: {data['username']} уже существует")

# Создаем автомобили
cars_data = [
    {'brand': 'Toyota Camry', 'plate': 'А123БВ177', 'status': 'free', 'mileage': 50000},
    {'brand': 'Kia Rio', 'plate': 'В456ГД178', 'status': 'free', 'mileage': 35000},
    {'brand': 'Hyundai Solaris', 'plate': 'Е789ЖЗ179', 'status': 'free', 'mileage': 42000},
    {'brand': 'Skoda Octavia', 'plate': 'К012ЛМ180', 'status': 'repair', 'mileage': 78000},
]

for car_data in cars_data:
    car, created = Car.objects.get_or_create(license_plate=car_data['plate'])
    if created:
        car.brand_model = car_data['brand']
        car.status = car_data['status']
        car.mileage = car_data['mileage']
        car.save()
        print(f"✅ Автомобиль: {car_data['brand']} ({car_data['plate']}) - создан")
    else:
        print(f"ℹ️ Автомобиль: {car_data['plate']} уже существует")

print("\n" + "=" * 60)
print("🎉 Инициализация завершена!")
print("=" * 60)
print("\n📋 Данные для входа:")
print("-" * 40)
print("Водитель 1:  driver1 / driver123")
print("Водитель 2:  driver2 / driver123")
print("Диспетчер:   dispatcher / disp123")
print("Руководство: manager / manager123")
print("-" * 40)
print("\n🚀 Запустите сервер: python manage.py runserver")
