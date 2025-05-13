# beauty_app/views/discount_views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from ..models import Discount, Service, Booking
from ..forms import DiscountForm
from ..permissions import AdminRequiredMixin

# beauty_app/views/discount_views.py

from django.utils import timezone

class DiscountListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Discount
    template_name = 'discount/discount_list.html'
    context_object_name = 'discounts'
    
    def get_queryset(self):
        # Show active discounts first, then order by start_date
        return Discount.objects.all().order_by(
            '-start_date', '-end_date'
        )
    
    # discount_views.py - Update the DiscountListView get_context_data method

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        now = timezone.now()
        
        # Properly filter active discounts
        active_discounts = Discount.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        )
        
        # Also get upcoming discounts
        upcoming_discounts = Discount.objects.filter(
            start_date__gt=now
        )
        
        # Add to context
        context['active_discounts'] = active_discounts
        context['active_count'] = active_discounts.count()
        
        context['upcoming_discounts'] = upcoming_discounts 
        context['upcoming_count'] = upcoming_discounts.count()
        
        context['expired_discounts'] = Discount.objects.filter(
            end_date__lt=now
        )
        context['expired_count'] = context['expired_discounts'].count()
        
        # Get services with no active OR upcoming discounts
        # Get services IDs that have either active or upcoming discounts
        services_with_discounts = set(list(active_discounts.values_list('service_id', flat=True)) + 
                                    list(upcoming_discounts.values_list('service_id', flat=True)))
        
        
        
        # Find active services NOT in the above set
        context['services_without_discount'] = Service.objects.filter(
            active=True
        ).exclude(id__in=services_with_discounts)
        print(context['services_without_discount'])
        
        return context

class DiscountDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Discount
    template_name = 'discount/discount_detail.html'
    context_object_name = 'discount'
    

# discount_views.py - Update the DiscountCreateView

class DiscountCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'discount/discount_form.html'
    success_url = reverse_lazy('discount_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pre-select service if passed in URL
        service_id = self.request.GET.get('service_id')
        if service_id:
            kwargs['initial'] = {'service': service_id}
        return kwargs
    
    def get(self, request, *args, **kwargs):
        # Check if service_id is in the request and validate it before showing the form
        service_id = request.GET.get('service_id')
        if service_id:
            service = Service.objects.filter(id=service_id).first()
            if service:
                # Check for existing active discount
                now = timezone.now()
                active_discount = Discount.objects.filter(
                    service=service,
                    start_date__lte=now,
                    end_date__gt=now
                ).first()
                
                if active_discount:
                    messages.error(
                        request, 
                        f"This service already has an active discount of {active_discount.percentage}% that ends on {active_discount.end_date.strftime('%Y-%m-%d')}."
                    )
                    return redirect('service_detail', pk=service_id)
                
                # Check for upcoming discount
                upcoming_discount = Discount.objects.filter(
                    service=service,
                    start_date__gt=now
                ).order_by('start_date').first()
                
                if upcoming_discount:
                    messages.error(
                        request, 
                        f"This service already has an upcoming discount of {upcoming_discount.percentage}% scheduled to start on {upcoming_discount.start_date.strftime('%Y-%m-%d')}."
                    )
                    return redirect('service_detail', pk=service_id)
        
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Discount created successfully.")
        return super().form_valid(form)

# discount_views.py - Update the DiscountUpdateView
class DiscountUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'discount/discount_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, "Discount updated successfully.")
        
        # If this is an active discount, update any associated bookings
        discount = form.instance
        if discount.is_active():
            # Get future bookings that use this service
            future_bookings = Booking.objects.filter(
                service=discount.service,
                date_time__gte=timezone.now(),
                status__in=['PENDING', 'CONFIRMED']
            )
            
            # Update the service_discount reference
            for booking in future_bookings:
                booking.service_discount = discount
                booking.save()
                
            if future_bookings.exists():
                messages.info(self.request, f"Updated discount information for {future_bookings.count()} upcoming bookings.")
                
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('discount_detail', kwargs={'pk': self.object.pk})

class DiscountDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Discount
    template_name = 'discount/discount_confirm_delete.html'
    success_url = reverse_lazy('discount_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Discount deleted successfully.")
        return super().delete(request, *args, **kwargs)
    


class ServiceDiscountHistoryView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Service
    template_name = 'service/service_discount_history.html'
    context_object_name = 'service'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_object()
        
        # Get all discounts for this service
        discounts = Discount.objects.filter(service=service).order_by('-start_date')
        
        # Group by status
        active_discounts = []
        upcoming_discounts = []
        expired_discounts = []
        
        for discount in discounts:
            if discount.is_active():
                active_discounts.append(discount)
            elif discount.is_upcoming():
                upcoming_discounts.append(discount)
            else:
                expired_discounts.append(discount)
        
        context['active_discounts'] = active_discounts
        context['upcoming_discounts'] = upcoming_discounts
        context['expired_discounts'] = expired_discounts
        context['all_discounts'] = discounts
        
        # Get discount usage statistics
        for discount in discounts:
            discount.usage_count = discount.total_usage()
            discount.total_saved = discount.total_savings()
        
        return context