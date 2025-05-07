# beauty_app/context_processors.py

from django.conf import settings

def beauty_settings(request):
    """
    Adds beauty parlor settings to the template context
    """
    return {
        'settings': {
            'BEAUTY_PARLOR_NAME': settings.BEAUTY_PARLOR_NAME,
            'BEAUTY_PARLOR_ADDRESS': settings.BEAUTY_PARLOR_ADDRESS,
            'BEAUTY_PARLOR_PHONE': settings.BEAUTY_PARLOR_PHONE,
            'BEAUTY_PARLOR_EMAIL': settings.BEAUTY_PARLOR_EMAIL,
            'BEAUTY_PARLOR_OPENING_HOURS': settings.BEAUTY_PARLOR_OPENING_HOURS,
            'BEAUTY_PARLOR_WORKING_DAYS': settings.BEAUTY_PARLOR_WORKING_DAYS,
        }
    }