# app/templatetags/custom_filters.py

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def percentage(value, total):
    """
    value / total * 100 hesablayır.
    total = 0 və ya boş olduqda 0 qaytarır.
    """
    try:
        if not total:
            return 0
        value = float(value or 0)
        total = float(total)
        if total == 0:
            return 0
        return (value / total) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return 0

