from django.shortcuts import render
from datetime import datetime, timedelta
class UnauthorizedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 401:
            return render(request, '401.html', status=401)
        return response
    



class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Update the session expiry time
            request.session.set_expiry(600)  # 10 minutes
            
        response = self.get_response(request)
        return response
    


# Add to beauty_app/middleware.py

import threading

_thread_local = threading.local()

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request in thread local
        _thread_local.request = request
        
        response = self.get_response(request)
        
        # Clear thread local to prevent memory leaks
        if hasattr(_thread_local, 'request'):
            del _thread_local.request
        
        return response


def get_current_user():
    """Get the current user from the request in thread local storage."""
    request = getattr(_thread_local, 'request', None)
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


def get_client_ip():
    """Get the client IP from the request in thread local storage."""
    request = getattr(_thread_local, 'request', None)
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    return None