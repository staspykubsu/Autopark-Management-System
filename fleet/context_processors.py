from .models import Request


def pending_requests_count(request):
    """Добавляет количество ожидающих заявок в контекст"""
    count = 0
    if request.user.is_authenticated:
        try:
            if request.user.profile.is_dispatcher():
                count = Request.objects.filter(status='new').count()
        except AttributeError:
            pass
    return {'pending_requests_count': count}