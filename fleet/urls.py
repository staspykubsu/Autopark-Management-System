from django.urls import path
from . import views

urlpatterns = [
    # Главная
    path('', views.HomeView.as_view(), name='home'),

    # Автомобили
    path('cars/', views.CarListView.as_view(), name='car_list'),
    path('cars/<int:pk>/', views.CarDetailView.as_view(), name='car_detail'),
    path('cars/add/', views.CarCreateView.as_view(), name='car_add'),
    path('cars/<int:pk>/edit/', views.CarUpdateView.as_view(), name='car_edit'),
    path('cars/<int:pk>/delete/', views.CarDeleteView.as_view(), name='car_delete'),

    # Водители
    path('drivers/', views.DriverListView.as_view(), name='driver_list'),
    path('drivers/add/', views.DriverCreateView.as_view(), name='driver_add'),
    path('drivers/<int:pk>/edit/', views.DriverUpdateView.as_view(), name='driver_edit'),
    path('drivers/<int:pk>/delete/', views.DriverDeleteView.as_view(), name='driver_delete'),

    # Заявки
    path('requests/', views.RequestListView.as_view(), name='request_list'),
    path('requests/add/', views.RequestCreateView.as_view(), name='request_add'),
    path('requests/<int:pk>/process/', views.RequestProcessView.as_view(), name='request_process'),

    # Поездки
    path('trips/', views.TripListView.as_view(), name='trip_list'),
    path('trips/add/', views.TripCreateView.as_view(), name='trip_add'),
    path('trips/<int:pk>/', views.TripDetailView.as_view(), name='trip_detail'),
    path('trips/<int:pk>/close/', views.TripCloseView.as_view(), name='trip_close'),

    # Отчеты
    path('reports/', views.ReportView.as_view(), name='report'),
]