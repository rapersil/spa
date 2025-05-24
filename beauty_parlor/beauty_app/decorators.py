# beauty_app/decorators.py

import functools
import threading

# Thread-local storage for the current request user and IP
_thread_locals = threading.local()


def set_current_user(user, ip_address=None):
    """Set the current user and IP address in thread-local storage."""
    _thread_locals.user = user
    _thread_locals.ip_address = ip_address


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, 'user', None)


def get_current_ip():
    """Get the current IP address from thread-local storage."""
    return getattr(_thread_locals, 'ip_address', None)


def clear_current_user():
    """Clear the current user and IP address from thread-local storage."""
    if hasattr(_thread_locals, 'user'):
        del _thread_locals.user
    if hasattr(_thread_locals, 'ip_address'):
        del _thread_locals.ip_address


def with_audit(view_func):
    """
    Decorator for views that sets the current user and IP address
    in thread-local storage for audit logging.
    """

    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        # Determine which argument is the request
        # For class-based views, args[0] is self and args[1] is request
        # For function-based views, args[0] is request
        if len(args) > 1 and hasattr(args[1], 'user'):
            request = args[1]  # Class-based view
        elif hasattr(args[0], 'user'):
            request = args[0]  # Function-based view
        else:
            # Can't find the request, just call the view
            return view_func(*args, **kwargs)

        # Set the current user and IP address
        if request.user.is_authenticated:
            set_current_user(request.user, getattr(request, 'audit_ip', None))

        try:
            # Call the view function
            return view_func(*args, **kwargs)
        finally:
            # Clear the current user and IP address
            clear_current_user()

    return wrapped_view
