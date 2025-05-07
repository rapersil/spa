# beauty_app/templatetags/audit_tags.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary using the key"""
    if not dictionary or not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")