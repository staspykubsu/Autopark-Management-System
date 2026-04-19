from django.db import models
from django.core.exceptions import ValidationError


class Car(models.Model):
    """Модель автомобиля (соответствует ЛР №1, №2, №4)"""

    STATUS_CHOICES = [
        ('free', 'Свободна'),
        ('trip', 'В рейсе'),
        ('repair', 'Ремонт'),
    ]

    brand_model = models.CharField('Марка и модель', max_length=100)
    license_plate = models.CharField('Госномер', max_length=10, unique=True)
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=STATUS_CHOICES,
        default='free'
    )
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
        """Проверка доступности автомобиля для выдачи"""
        return self.status == 'free'


class Driver(models.Model):
    """Модель водителя"""

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


class Request(models.Model):
    """Модель заявки на получение автомобиля"""

    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]

    requester_name = models.CharField('ФИО заявителя', max_length=100)
    trip_date = models.DateField('Дата поездки')
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=STATUS_CHOICES,
        default='new'
    )
    rejection_reason = models.TextField('Причина отказа', blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.requester_name} - {self.trip_date}'


class Trip(models.Model):
    """Модель поездки (смены) - центральная сущность системы"""

    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        verbose_name='Автомобиль',
        related_name='trips'
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

    # Выезд
    departure_date = models.DateTimeField('Дата и время выезда')
    departure_mileage = models.IntegerField('Пробег при выезде')

    # Возврат
    return_date = models.DateTimeField('Дата и время возврата', null=True, blank=True)
    return_mileage = models.IntegerField('Пробег при возврате', null=True, blank=True)

    class Meta:
        verbose_name = 'Поездка'
        verbose_name_plural = 'Поездки'
        ordering = ['-departure_date']

    def __str__(self):
        return f'{self.car} - {self.driver} ({self.departure_date.strftime("%d.%m.%Y %H:%M")})'

    def clean(self):
        """Валидация данных поездки"""
        if self.return_mileage and self.departure_mileage:
            if self.return_mileage < self.departure_mileage:
                raise ValidationError({
                    'return_mileage': 'Пробег при возврате не может быть меньше пробега при выезде'
                })

    def distance(self):
        """Расчет пройденного расстояния (км)"""
        if self.return_mileage and self.departure_mileage:
            return self.return_mileage - self.departure_mileage
        return None

    def is_active(self):
        """Проверка, активна ли поездка (не завершена)"""
        return self.return_date is None

    def save(self, *args, **kwargs):
        """Переопределение save для автоматического обновления пробега автомобиля"""
        is_new = self.pk is None

        if not is_new:
            old_trip = Trip.objects.get(pk=self.pk)
            # Если поездка завершается (была активна, теперь есть return_mileage)
            if old_trip.return_mileage is None and self.return_mileage is not None:
                # Обновляем пробег автомобиля
                distance = self.return_mileage - self.departure_mileage
                self.car.mileage += distance
                self.car.status = 'free'
                self.car.save()

        super().save(*args, **kwargs)