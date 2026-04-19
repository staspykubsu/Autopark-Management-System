from django import template

register = template.Library()

@register.filter(name='div')
def div_filter(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter(name='mul')
def mul_filter(value, arg):
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0