from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def qty_az(value):
    if value is None:
        return '—'
    num = Decimal(str(value))
    if num == 0:
        return '0'
    formatted = f'{num:.1f}'.rstrip('0').rstrip('.')
    return formatted.replace('.', ',')


@register.filter
def delta_in(value):
    if value is None:
        return '—'
    num = Decimal(str(value))
    if num == 0:
        return '0'
    return f'+{qty_az(num)}'


@register.filter
def delta_out(value):
    if value is None:
        return '—'
    num = Decimal(str(value))
    if num == 0:
        return '0'
    return f'−{qty_az(num)}'
