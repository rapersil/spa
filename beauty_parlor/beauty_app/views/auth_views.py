# beauty_app/views/auth_views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login as auth_login, logout
from django.views.generic import ListView, FormView, RedirectView
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic.detail import SingleObjectMixin
from django.core.exceptions import PermissionDenied

from ..models import CustomUser
from ..permissions import AdminRequiredMixin

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        # Get the authenticated user before calling super().form_valid()
        user = form.get_user()
        
        # Check permission
        if user.user_type not in ['STAFF', 'ADMIN', 'SUPERADMIN']:
            form.add_error(None, "You don't have permission to access this system.")
            return self.form_invalid(form)
        
        # Check if password change is required
        if user.password_change_required:
            # First authenticate the user properly
            auth_login(self.request, user)
            
            # Store the user ID in session
            self.request.session['password_change_required_user_id'] = user.id
            
            # Add a message
            messages.warning(self.request, "You must change your password before continuing.")
            
            # Redirect to password change page
            return redirect('password_change_required')
        
        # Standard login flow
        result = super().form_valid(form)
        messages.success(self.request, f"Welcome back, {user.get_full_name() or user.username}!")
        return result
    
    def get_success_url(self):
        return reverse_lazy('dashboard')

def logout_view(request):
    if request.user.is_authenticated:
        messages.info(request, "You have been logged out successfully.")
        logout(request)
    return redirect('login')

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'auth/password_change.html'
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # If this was a required password change, update the user's flag
        user = self.request.user
        if user.password_change_required:
            user.password_change_required = False
            user.save(update_fields=['password_change_required'])
        
        messages.success(self.request, "Your password has been changed successfully.")
        return response

class PasswordChangeRequiredView(LoginRequiredMixin, FormView):
    template_name = 'auth/password_change_required.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('dashboard')
    
    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        # Check if user is logged in but hasn't been redirected from login
        if request.user.is_authenticated and 'password_change_required_user_id' not in request.session:
            # If they're required to change password, keep them here
            if request.user.password_change_required:
                request.session['password_change_required_user_id'] = request.user.id
            # Otherwise redirect to dashboard
            else:
                return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user_id = self.request.session.get('password_change_required_user_id', self.request.user.id)
        kwargs['user'] = get_object_or_404(CustomUser, id=user_id)
        return kwargs
    
    def form_valid(self, form):
        form.save()
        user = form.user
        user.password_change_required = False
        user.save(update_fields=['password_change_required'])
        
        # Clear the session
        if 'password_change_required_user_id' in self.request.session:
            del self.request.session['password_change_required_user_id']
        
        messages.success(self.request, "Your password has been changed successfully.")
        return super().form_valid(form)

# Admin Password Reset Views
class AdminPasswordResetListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'auth/admin_password_reset_list.html'
    context_object_name = 'users'
    
    def get_queryset(self):
        # Only show staff and admin users, not the current admin
        return CustomUser.objects.filter(
            user_type__in=['STAFF', 'ADMIN']
        ).exclude(id=self.request.user.id).order_by('user_type', 'first_name', 'last_name')

class AdminPasswordResetView(LoginRequiredMixin, AdminRequiredMixin, SingleObjectMixin, FormView):
    model = CustomUser
    template_name = 'auth/admin_password_reset.html'
    form_class = SetPasswordForm

    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.object = None

    def get_object(self, queryset=None):
        # Ensure the user can't reset their own password through this view
        obj = super().get_object(queryset)
        if obj.id == self.request.user.id:
            raise PermissionDenied("You cannot reset your own password with this form.")
        return obj
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.get_object()
        return kwargs
    
    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        return super().get_context_data(**kwargs)
    
    def form_valid(self, form):
        user = form.user
        form.save()
        
        # Mark the user as requiring a password change
        user.password_change_required = True
        user.save(update_fields=['password_change_required'])
        
        messages.success(
            self.request, 
            f"Password has been reset for {user.get_full_name() or user.username}. They will be required to change it at next login."
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('admin_password_reset_list')