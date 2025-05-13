# beauty_app/views/user_views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from ..models import CustomUser, Sale, Booking, Customer, Service,Discount
from ..forms import StaffCreationForm, CustomUserUpdateForm, ProfileUpdateForm
from ..permissions import AdminRequiredMixin

class StaffListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'user/staff_list.html'
    context_object_name = 'staff'
    
    def get_queryset(self):
        # Only show staff and admin users, not superadmin
        queryset = CustomUser.objects.filter(
            user_type__in=['STAFF', 'ADMIN','COMMONSTAFF']
        ).order_by('user_type', 'first_name', 'last_name')
        
        # Apply search if provided
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(user_id__iexact=query)
            )
            
        return queryset

class StaffDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'user/staff_detail.html'
    context_object_name = 'staff_member'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_member = self.object
        
        # Get recent bookings created by this staff member (existing functionality)
        context['recent_bookings'] = staff_member.created_bookings.all().order_by('-created_at')[:5]
        
        # Enhanced activity tracking - Bookings updated
        context['updated_bookings'] = Booking.objects.filter(
            updated_by=staff_member
        ).exclude(
            created_by=staff_member  # Exclude bookings they created themselves
        ).order_by('-updated_at')[:5]
        
        # Booking status changes (to completed/cancelled)
        context['completed_bookings'] = Booking.objects.filter(
            updated_by=staff_member,
            status='COMPLETED'
        ).order_by('-updated_at')[:5]
        
        context['cancelled_bookings'] = Booking.objects.filter(
            updated_by=staff_member,
            status='CANCELLED'
        ).order_by('-updated_at')[:5]
        
        # Customer activity
        context['created_customers'] = Customer.objects.filter(
            created_by=staff_member
        ).order_by('-date_joined')[:5]
        
        # Sales activity
        context['recorded_sales'] = Sale.objects.filter(
            created_by=staff_member
        ).order_by('-payment_date')[:5]
        
        # Activity counts for summary metrics
        context['activity_counts'] = {
            'bookings_created': staff_member.created_bookings.count(),
            'bookings_updated': Booking.objects.filter(updated_by=staff_member).exclude(created_by=staff_member).count(),
            'customers_created': Customer.objects.filter(created_by=staff_member).count(),
            'sales_recorded': Sale.objects.filter(created_by=staff_member).count(),
        }
        
        # Service and discount management (for admins)
        if staff_member.user_type in ['ADMIN', 'SUPERADMIN']:
            context['created_services'] = Service.objects.filter(created_by=staff_member).order_by('-id')[:5]
            context['created_discounts'] = Discount.objects.filter(created_by=staff_member).order_by('-start_date')[:5]
            
            context['activity_counts'].update({
                'services_created': Service.objects.filter(created_by=staff_member).count(),
                'discounts_created': Discount.objects.filter(created_by=staff_member).count(),
            })
        
        # Time-based metrics
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        context['time_based_activity'] = {
            'bookings_today': staff_member.created_bookings.filter(created_at__date=today).count(),
            'bookings_this_week': staff_member.created_bookings.filter(created_at__date__gte=week_start).count(),
            'bookings_this_month': staff_member.created_bookings.filter(created_at__date__gte=month_start).count(),
            'sales_today': Sale.objects.filter(created_by=staff_member, payment_date__date=today).count(),
            'sales_this_week': Sale.objects.filter(created_by=staff_member, payment_date__date__gte=week_start).count(),
            'sales_this_month': Sale.objects.filter(created_by=staff_member, payment_date__date__gte=month_start).count(),
        }
        
        # Sales amount metrics
        from django.db.models import Sum
        
        context['sales_metrics'] = {
            'total_sales_amount': Sale.objects.filter(created_by=staff_member).aggregate(
                total=Sum('payment_amount'))['total'] or 0,
            'today_sales_amount': Sale.objects.filter(
                created_by=staff_member, payment_date__date=today).aggregate(
                total=Sum('payment_amount'))['total'] or 0,
            'week_sales_amount': Sale.objects.filter(
                created_by=staff_member, payment_date__date__gte=week_start).aggregate(
                total=Sum('payment_amount'))['total'] or 0,
            'month_sales_amount': Sale.objects.filter(
                created_by=staff_member, payment_date__date__gte=month_start).aggregate(
                total=Sum('payment_amount'))['total'] or 0,
        }
        
        return context



class StaffCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = CustomUser
    form_class = StaffCreationForm
    template_name = 'user/staff_form.html'
    success_url = reverse_lazy('staff_list')
    
    def form_valid(self, form):
        # Set password_change_required flag
        user = form.save(commit=False)
        user.password_change_required = True
        user.save()
        
        messages.success(
            self.request, 
            f"Staff member {user.get_full_name() or user.username} created successfully. They will be required to change their password at first login."
        )
        return super().form_valid(form)

class StaffUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserUpdateForm
    template_name = 'user/staff_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, "Staff member updated successfully.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('staff_detail', kwargs={'pk': self.object.pk})

class ProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileUpdateForm
    template_name = 'user/profile.html'
    success_url = reverse_lazy('profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)