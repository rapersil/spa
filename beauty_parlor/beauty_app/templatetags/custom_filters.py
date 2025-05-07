# beauty_app/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def mult(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return ''

@register.filter
def subtract(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def multiply(value, arg):
    """Alias for mult filter"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
    

@register.filter
def percentage(value, total):
    """Calculate percentage safely"""
    try:
        if int(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
    

@register.filter
def sum_attr(queryset, attr):
    """Sum a specific attribute for all objects in a queryset"""
    if queryset:
        return sum(getattr(obj, attr, 0) for obj in queryset)
    return 0


@register.filter
def modulo(value, arg):
    """Returns the remainder of value divided by arg"""
    return int(value) % int(arg)

# @register.filter
# def get_item(dictionary, key):
#     """Gets an item from a dictionary using the key"""
#     return dictionary.get(key, [])



@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary using the key"""
    if not dictionary or not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")