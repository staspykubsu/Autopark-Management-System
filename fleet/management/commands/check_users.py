from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Проверяет пользователей и создает админа если их нет'

    def handle(self, *args, **options):
        self.stdout.write("=" * 50)
        self.stdout.write("Список пользователей:")
        self.stdout.write("=" * 50)
        
        for user in User.objects.all():
            self.stdout.write(f"ID: {user.id}, Username: {user.username}, Email: {user.email}")
        
        if User.objects.count() == 0:
            self.stdout.write(self.style.WARNING("\nПользователей нет. Создаем администратора..."))
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS(f"✅ Создан пользователь с ID: {admin.id}"))
            self.stdout.write(self.style.SUCCESS(f"   Логин: admin"))
            self.stdout.write(self.style.SUCCESS(f"   Пароль: admin123"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Всего пользователей: {User.objects.count()}"))