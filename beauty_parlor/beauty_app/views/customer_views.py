from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from ..models import Customer, Booking, Sale, AdditionalService
from ..forms import CustomerForm, CustomerSearchForm
from ..permissions import StaffRequiredMixin, AdminRequiredMixin

from django.db.models import Count
from django.utils import timezone

from django.db.models import Count, Sum
from django.utils import timezone


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


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class CustomerDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Customer
    template_name = 'customer/customer_detail.html'
    context_object_name = 'customer'
    # Corrected attribute name (was "pagenated_by")
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Get all bookings for this customer (ordered by date)
        all_bookings = Booking.objects.filter(
            customer=self.object
        ).order_by('-date_time')

        # Implement pagination for bookings
        page = self.request.GET.get('page', 1)
        paginator = Paginator(all_bookings, self.paginate_by)

        try:
            paginated_bookings = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            paginated_bookings = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page of results
            paginated_bookings = paginator.page(paginator.num_pages)

        # Add paginated bookings to context
        context['booking_history'] = paginated_bookings
        context['booking_count'] = all_bookings.count()

        # Keep a small list of truly recent bookings for quick reference
        context['recent_bookings'] = all_bookings[:5]

        # Calculate comprehensive service preferences (main services + additional services)
        service_preferences = self.get_comprehensive_service_preferences()
        context['service_counts'] = service_preferences

        # Count completed bookings
        context['completed_bookings_count'] = Booking.objects.filter(
            customer=self.object,
            status='COMPLETED'
        ).count()

        # Count upcoming confirmed bookings
        context['upcoming_bookings_count'] = Booking.objects.filter(
            customer=self.object,
            date_time__gte=today,
            status__in=['PENDING', 'CONFIRMED'],
        ).count()

        # Count cancelled bookings
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

        # Calculate total spent (if user has permission)
        if hasattr(self.request.user, 'user_type') and self.request.user.user_type in ['ADMIN', 'SUPERADMIN']:
            context['total_spent'] = Sale.objects.filter(
                booking__customer=self.object,
                booking__status='COMPLETED'
            ).aggregate(total=Sum('payment_amount'))['total'] or 0

        context['today'] = today

        return context

    def get_comprehensive_service_preferences(self):
        """
        Calculate service preferences including both main booking services
        and additional services for a more complete picture.
        """
        from collections import defaultdict

        service_counts = defaultdict(int)

        # Get main services from bookings
        main_services = Booking.objects.filter(
            customer=self.object
        ).values('service__name').annotate(
            count=Count('service')
        )

        for service in main_services:
            service_counts[service['service__name']] += service['count']

        # Get additional services from bookings
        additional_services = AdditionalService.objects.filter(
            booking__customer=self.object
        ).values('name').annotate(
            count=Count('name')
        )

        for service in additional_services:
            service_counts[service['name']] += service['count']

        # Convert to list of dictionaries sorted by count (descending)
        service_list = []
        for service_name, count in service_counts.items():
            service_list.append({
                'service__name': service_name,
                'count': count,
                'is_additional': service_name not in [s['service__name'] for s in main_services]
            })

        # Sort by count (highest first)
        service_list.sort(key=lambda x: x['count'], reverse=True)

        return service_list


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