# beauty_app/views/customer_views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from ..models import Customer, Booking,Sale
from ..forms import CustomerForm, CustomerSearchForm
from ..permissions import StaffRequiredMixin, AdminRequiredMixin

class CustomerListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Customer
    template_name = 'customer/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Customer.objects.all().order_by('first_name', 'last_name')
        
        # Apply search filter if provided
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                # Q(email__icontains=query) |
                Q(phone__icontains=query) |
                Q(customer_id__iexact=query)
            )
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CustomerSearchForm(self.request.GET or None)
        return context

from django.db.models import Count
from django.utils import timezone

from django.db.models import Count, Sum
from django.utils import timezone

class CustomerDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Customer
    template_name = 'customer/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Add recent bookings for this customer
        context['recent_bookings'] = Booking.objects.filter(
            customer=self.object
        ).order_by('-date_time')[:5]
        
        # Calculate service preferences
        service_counts = Booking.objects.filter(
            customer=self.object
        ).values('service__name').annotate(
            count=Count('service')
        ).order_by('-count')[:5]
        
        # Count completed bookings
        context['completed_bookings_count'] = Booking.objects.filter(
            customer=self.object,
            status='COMPLETED'
        ).count()
        
        # Count upcoming confirmed bookings
        context['upcoming_bookings_count'] = Booking.objects.filter(
            customer=self.object,
            date_time__gte=today,
            status__in=['PENDING', 'CONFIRMED'],  # Include 'PENDING' and 'CONFIRMED'
        ).count()

        #count cancelled bookings
        context['cancelled_bookings_count'] = Booking.objects.filter(
            customer=self.object,
            status='CANCELLED'
        ).count()
        
        # Get last completed booking
        last_completed = Booking.objects.filter(
            customer=self.object,
            status='COMPLETED'
        ).order_by('-date_time').first()
        
        context['last_completed_booking'] = last_completed
        
        # Calculate total spent (if you need this)
        if hasattr(self.request.user, 'user_type') and self.request.user.user_type in ['ADMIN', 'SUPERADMIN']:
            context['total_spent'] = Sale.objects.filter(
                booking__customer=self.object,
                booking__status='COMPLETED'
            ).aggregate(total=Sum('payment_amount'))['total'] or 0
        
        context['service_counts'] = service_counts
        context['today'] = today
        
        return context

class CustomerCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/customer_form.html'
    success_url = reverse_lazy('customer_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Customer created successfully.")
        return super().form_valid(form)

class CustomerUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/customer_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, "Customer updated successfully.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('customer_detail', kwargs={'pk': self.object.pk})