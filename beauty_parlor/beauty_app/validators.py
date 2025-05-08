# validators.py

from django.core.exceptions import ValidationError
import re

def email_validator(value):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid email address.")
    return value

def phone_validator(value):
    pattern = r'^\+?[0-9]{10,15}$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid phone number (10-15 digits).")
    return value

def price_validator(value):
    if value <= 0:
        raise ValidationError("Price must be greater than zero.")
    return value

def discount_validator(value):
    if value < 0 or value > 100:
        raise ValidationError("Discount must be between 0 and 100.")
    return value

def date_time_validator(value):
    from django.utils import timezone
    if value < timezone.now():
        raise ValidationError("Date and time cannot be in the past.")
    return value