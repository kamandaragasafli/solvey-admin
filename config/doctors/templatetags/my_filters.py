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
    except:
        return ''
@register.filter
def index(sequence, position):
    try:
        return sequence[position]
    except IndexError:
        return None