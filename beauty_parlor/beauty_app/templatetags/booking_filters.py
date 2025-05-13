
from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """Split a string into a list by delimiter"""
    return value.split(delimiter)

@register.filter
def time_display(hour):
    """Format hour for display (9 -> 9 AM, 13 -> 1 PM)"""
    hour = int(hour)
    if hour < 12:
        return f"{hour} AM"
    elif hour == 12:
        return "12 PM"
    else:
        return f"{hour - 12} PM"

@register.filter
def compute_percent(time, start_hour, end_hour):
    """Compute percentage position for timeline visualization"""
    if isinstance(time, str):
        # Parse time string
        try:
            time = timezone.datetime.strptime(time, '%H:%M').time()
        except ValueError:
            return 0
    
    total_minutes = (int(end_hour) - int(start_hour)) * 60
    
    # Handle datetime or time objects
    if hasattr(time, 'hour'):
        minutes_since_start = (time.hour - int(start_hour)) * 60 + time.minute
    else:
        # Handle datetime object
        minutes_since_start = (time.hour - int(start_hour)) * 60 + time.minute
    
    return (minutes_since_start / total_minutes) * 100
@register.filter
def duration_percent(duration, total_minutes):
    """Compute width percentage for a booking duration"""
    return (duration / total_minutes) * 100