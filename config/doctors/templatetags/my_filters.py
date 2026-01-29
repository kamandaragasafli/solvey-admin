from django import template
from builtins import zip as builtin_zip

register = template.Library()

@register.filter
def zip(a, b):
    return list(builtin_zip(a, b))

@register.filter
def index(sequence, i):
    try:
        return sequence[i]
    except Exception:
        return ''

@register.filter
def before_dash(value):
    """
    '19 POL-Bakı bölgə-3' -> '19 POL'
    İlk '-' işarəsindən sonrasını silir.
    """
    if value is None:
        return ''
    s = str(value)
    return s.split('-', 1)[0].strip()
