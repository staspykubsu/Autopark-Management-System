from django.urls import path
from . import views

urlpatterns = [
    # Авторизация и профиль
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    
    # Управление ролями
    path('manage-roles/', views.ManageRolesView.as_view(), name='manage_roles'),
    path('change-role/<int:profile_id>/', views.change_role, name='change_role'),
    
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
    path('drivers/<int:pk>/', views.DriverDetailView.as_view(), name='driver_detail'),
    path('drivers/add/', views.DriverCreateView.as_view(), name='driver_add'),
    path('drivers/<int:pk>/edit/', views.DriverUpdateView.as_view(), name='driver_edit'),
    path('drivers/<int:pk>/delete/', views.DriverDeleteView.as_view(), name='driver_delete'),
    
    # Заявки
    path('requests/', views.RequestListView.as_view(), name='request_list'),
    path('requests/add/', views.RequestCreateView.as_view(), name='request_add'),
    path('requests/<int:pk>/process/', views.RequestProcessView.as_view(), name='request_process'),
    
    # Мои поездки (для водителя)
    path('my-trips/', views.MyTripsView.as_view(), name='my_trips'),
    path('my-trips/<int:trip_id>/start/', views.TripStartView.as_view(), name='trip_start'),
    path('my-trips/<int:trip_id>/end/', views.TripEndView.as_view(), name='trip_end'),
    
    # Все поездки (для диспетчера и руководства)
    path('trips/', views.TripListView.as_view(), name='trip_list'),
    path('trips/<int:pk>/', views.TripDetailView.as_view(), name='trip_detail'),
    
    # Отчеты
    path('reports/', views.ReportView.as_view(), name='report'),
]