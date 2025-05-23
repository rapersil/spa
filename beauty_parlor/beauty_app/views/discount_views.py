# beauty_app/views/discount_views.py - Updated views with name field

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView,FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from ..models import Discount, Service, Booking
from ..forms import DiscountForm
from ..permissions import AdminRequiredMixin

class DiscountListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Discount
    template_name = 'discount/discount_list.html'
    context_object_name = 'discounts'
    
    def get_queryset(self):
        # Show active discounts first, then order by start_date
        return Discount.objects.all().order_by(
            '-start_date', '-end_date'
        )
    
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
        
        return context

class DiscountDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Discount
    template_name = 'discount/discount_detail.html'
    context_object_name = 'discount'

class DiscountCreateView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    form_class = DiscountForm
    template_name = 'discount/discount_form.html'
    success_url = reverse_lazy('discount_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pre-select service if passed in URL
        service_id = self.request.GET.get('service_id')
        if service_id:
            kwargs['initial'] = {
                'discount_type': 'single',
                'single_service': service_id
            }
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add extra context for the template
        service_id = self.request.GET.get('service_id')
        if service_id:
            context['selected_service'] = Service.objects.filter(id=service_id).first()
        
        context['is_update'] = False
        context['active_services_count'] = Service.objects.filter(active=True).count()
        return context
    
    def form_valid(self, form):
        selected_services = form.get_selected_services()
        discount_name = form.cleaned_data['name']
        
        if not selected_services:
            messages.error(self.request, "No services selected for discount.")
            return self.form_invalid(form)
        
        # Create discount for each selected service
        discounts_created = 0
        for service in selected_services:
            # For multiple services, append service name to make it unique
            if len(selected_services) > 1:
                service_specific_name = f"{discount_name} - {service.name}"
            else:
                service_specific_name = discount_name
                
            discount = Discount(
                name=service_specific_name,
                service=service,
                percentage=form.cleaned_data['percentage'],
                start_date=form.cleaned_data['start_date'],
                end_date=form.cleaned_data['end_date'],
                created_by=self.request.user
            )
            discount.save()
            discounts_created += 1
        
        # Customize success message based on how many discounts were created
        if discounts_created == 1:
            messages.success(self.request, f"Discount '{discount_name}' created successfully for '{selected_services[0].name}'.")
        else:
            messages.success(self.request, f"Discount '{discount_name}' created successfully for {discounts_created} services.")
        
        return super().form_valid(form)

class DiscountUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'discount/discount_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        context['discount'] = self.get_object()
        return context
    
    def form_valid(self, form):
        discount = self.get_object()
        
        # Update the existing discount record
        discount.name = form.cleaned_data['name']
        discount.percentage = form.cleaned_data['percentage']
        discount.start_date = form.cleaned_data['start_date']
        discount.end_date = form.cleaned_data['end_date']
        discount.save()
        
        messages.success(self.request, f"Discount '{discount.name}' for '{discount.service.name}' updated successfully.")
        return redirect('discount_detail', pk=discount.pk)
    
    def get_success_url(self):
        return reverse_lazy('discount_detail', kwargs={'pk': self.object.pk})

class DiscountDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Discount
    template_name = 'discount/discount_confirm_delete.html'
    success_url = reverse_lazy('discount_list')
    
    def delete(self, request, *args, **kwargs):
        discount = self.get_object()
        messages.success(request, f"Discount '{discount.name}' deleted successfully.")
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