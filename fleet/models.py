from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    """Расширенный профиль пользователя с ролью"""
    
    ROLE_CHOICES = [
        ('driver', 'Водитель'),
        ('dispatcher', 'Диспетчер'),
        ('manager', 'Руководство'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES, default='driver')
    phone = models.CharField('Телефон', max_length=15, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'
    
    def is_driver(self):
        return self.role == 'driver'
    
    def is_dispatcher(self):
        return self.role == 'dispatcher'
    
    def is_manager(self):
        return self.role == 'manager'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Car(models.Model):
    """Модель автомобиля"""
    
    STATUS_CHOICES = [
        ('free', 'Свободна'),
        ('trip', 'В рейсе'),
        ('repair', 'Ремонт'),
    ]

    brand_model = models.CharField('Марка и модель', max_length=100)
    license_plate = models.CharField('Госномер', max_length=10, unique=True)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='free')
    mileage = models.IntegerField('Текущий пробег', default=0)

    class Meta:
        verbose_name = 'Автомобиль'
        verbose_name_plural = 'Автомобили'
        ordering = ['brand_model']

    def __str__(self):
        return f'{self.brand_model} ({self.license_plate})'

    def clean(self):
        if self.mileage < 0:
            raise ValidationError({'mileage': 'Пробег не может быть отрицательным'})

    def is_available(self):
        return self.status == 'free'


class Driver(models.Model):
    """Модель водителя (связана с User)"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='driver',
        verbose_name='Пользователь'
    )
    name = models.CharField('ФИО', max_length=100)
    license_number = models.CharField(
        'Номер водительского удостоверения',
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )
    phone = models.CharField('Телефон', max_length=15, blank=True, null=True)

    class Meta:
        verbose_name = 'Водитель'
        verbose_name_plural = 'Водители'
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def has_active_request(self):
        """Проверяет, есть ли у водителя активная (новая или одобренная) заявка"""
        return self.requests.filter(status__in=['new', 'approved']).exists()
    
    def has_pending_trip(self):
        """Проверяет, есть ли у водителя заявка, по которой еще не совершена поездка"""
        # Находим одобренные заявки, по которым еще нет поездки
        approved_requests = self.requests.filter(status='approved')
        for req in approved_requests:
            if not hasattr(req, 'trip') or req.trip is None:
                return True
        return False
    
    def has_active_trip(self):
        """Проверяет, есть ли у водителя активная поездка"""
        return self.trips.filter(return_date__isnull=True).exists()
    
    def can_create_request(self):
        """Может ли водитель создать новую заявку"""
        return not self.has_active_request() and not self.has_pending_trip() and not self.has_active_trip()


class Request(models.Model):
    """Модель заявки на получение автомобиля"""
    
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        verbose_name='Водитель',
        related_name='requests'
    )
    trip_date = models.DateField('Дата поездки')
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='new')
    rejection_reason = models.TextField('Причина отказа', blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Обработал',
        related_name='processed_requests'
    )
    processed_at = models.DateTimeField('Дата обработки', null=True, blank=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.driver.name} - {self.trip_date}'
    
    def clean(self):
        # Проверка, что дата поездки не в прошлом
        if self.trip_date and self.trip_date < timezone.now().date():
            raise ValidationError({'trip_date': 'Дата поездки не может быть в прошлом'})
        
        # Проверки для нового объекта (еще не сохранен в БД)
        if not self.pk:
            # Проверка на наличие driver_id (если driver уже назначен)
            if hasattr(self, 'driver_id') and self.driver_id:
                try:
                    driver = Driver.objects.get(id=self.driver_id)
                    if driver.has_active_request():
                        raise ValidationError('У вас уже есть активная заявка (новая или одобренная)')
                    if driver.has_pending_trip():
                        raise ValidationError('У вас есть одобренная заявка, по которой еще не совершена поездка')
                    if driver.has_active_trip():
                        raise ValidationError('У вас есть активная поездка. Завершите её перед созданием новой заявки')
                except Driver.DoesNotExist:
                    pass
        else:
            # Для существующего объекта - дополнительные проверки при изменении статуса
            pass


class Trip(models.Model):
    """Модель поездки (смены)"""
    
    car = models.ForeignKey(
        Car,
        on_delete=models.SET_NULL,  # Изменено с CASCADE на SET_NULL
        verbose_name='Автомобиль',
        related_name='trips',
        null=True,  # Разрешаем NULL
        blank=True  # Разрешаем пустое значение в формах
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        verbose_name='Водитель',
        related_name='trips'
    )
    request = models.OneToOneField(
        Request,
        on_delete=models.SET_NULL,
        verbose_name='Заявка',
        null=True,
        blank=True,
        related_name='trip'
    )

    departure_date = models.DateTimeField('Дата и время выезда', null=True, blank=True)
    departure_mileage = models.IntegerField('Пробег при выезде', null=True, blank=True)
    return_date = models.DateTimeField('Дата и время возврата', null=True, blank=True)
    return_mileage = models.IntegerField('Пробег при возврате', null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_trips',
        verbose_name='Создал'
    )
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_trips',
        verbose_name='Закрыл'
    )

    class Meta:
        verbose_name = 'Поездка'
        verbose_name_plural = 'Поездки'
        ordering = ['-departure_date']

    def __str__(self):
        if self.departure_date:
            return f'{self.car if self.car else "Без авто"} - {self.driver} ({self.departure_date.strftime("%d.%m.%Y %H:%M")})'
        return f'Заявка #{self.request.pk if self.request else "?"} - {self.driver} (ожидает начала)'

    def clean(self):
        if self.return_mileage and self.departure_mileage:
            if self.return_mileage < self.departure_mileage:
                raise ValidationError({
                    'return_mileage': 'Пробег при возврате не может быть меньше пробега при выезде'
                })

    def distance(self):
        if self.return_mileage and self.departure_mileage:
            return self.return_mileage - self.departure_mileage
        return None

    def is_active(self):
        return self.departure_date is not None and self.return_date is None
    
    def is_waiting(self):
        return self.departure_date is None
    
    def start_trip(self, car):
        """Начать поездку (вызывается водителем)"""
        if self.departure_date is not None:
            raise ValidationError('Поездка уже начата')
        if car.status != 'free':
            raise ValidationError('Автомобиль недоступен')
        
        self.car = car
        self.departure_date = timezone.now()
        self.departure_mileage = car.mileage
        car.status = 'trip'
        car.save()
        self.save()
    
    def end_trip(self, return_mileage):
        """Завершить поездку (вызывается водителем)"""
        if self.departure_date is None:
            raise ValidationError('Поездка еще не начата')
        if self.return_date is not None:
            raise ValidationError('Поездка уже завершена')
        if return_mileage < self.departure_mileage:
            raise ValidationError('Пробег при возврате не может быть меньше пробега при выезде')
        
        self.return_date = timezone.now()
        self.return_mileage = return_mileage
        distance = return_mileage - self.departure_mileage
        self.car.mileage += distance
        self.car.status = 'free'
        self.car.save()
        self.save()