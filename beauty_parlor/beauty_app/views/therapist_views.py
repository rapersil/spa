

from datetime import timedelta, timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DeleteView
from django.views.generic.edit import FormView

from beauty_app.forms import TherapistAssignmentForm
from django.contrib import messages
from beauty_app.models import Booking,AdditionalService, CustomUser, Service, BookingTherapistAssignment
from beauty_app.permissions import StaffRequiredMixin

class TherapistAssignmentView(LoginRequiredMixin, StaffRequiredMixin, FormView):
    template_name = 'booking/therapist_assignment.html'
    form_class = TherapistAssignmentForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        booking_id = self.kwargs.get('booking_id')
        self.booking = get_object_or_404(Booking, pk=booking_id)
        kwargs['booking'] = self.booking
        return kwargs
    
    def get_success_url(self):
        return reverse('booking_detail', kwargs={'pk': self.booking.pk})
    
    def form_valid(self, form):
        # Get form data
        therapist = form.cleaned_data['therapist']
        is_primary = form.cleaned_data.get('is_primary', True)  # Default to primary if not specified
        
        # Get the exact booking time
        booking_time = self.booking.date_time
        
        # Look for conflicts with other bookings at the exact same time
        conflicts = BookingTherapistAssignment.objects.filter(
            therapist=therapist,
            booking__date_time=booking_time,  # Exact time match
            booking__status__in=['PENDING', 'CONFIRMED']
        ).exclude(booking=self.booking)
        
        if conflicts.exists():
            # Show warning but allow assignment
            messages.warning(
                self.request, 
                f"Warning: {therapist.get_full_name()} has another booking scheduled at the same time. "
                f"Assignment was created but there will be a scheduling conflict."
            )
        
        # Create or update the therapist assignment
        try:
            # Try to find existing assignment
            assignment = BookingTherapistAssignment.objects.get(
                booking=self.booking,
                therapist=therapist
            )
            assignment.is_primary = is_primary
            assignment.assigned_by = self.request.user
            assignment.updated_at = timezone.now()
            assignment.save()
            messages.success(self.request, f"Updated therapist assignment for this booking.")
        except BookingTherapistAssignment.DoesNotExist:
            # Create new assignment
            BookingTherapistAssignment.objects.create(
                booking=self.booking,
                therapist=therapist,
                is_primary=is_primary,
                assigned_by=self.request.user
            )
            messages.success(self.request, f"Assigned {therapist.get_full_name()} to this booking.")
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.booking
        
        # Get the services associated with this booking
        main_service = self.booking.service
        
        # Get additional services
        additional_services = []
        add_service_objs = AdditionalService.objects.filter(booking=self.booking)
        for add_svc in add_service_objs:
            try:
                service = Service.objects.get(name=add_svc.name)
                additional_services.append(service)
            except Service.DoesNotExist:
                # Add the AdditionalService object itself if the Service can't be found
                additional_services.append(add_svc)
        
        # Get existing therapist assignments
        assignments = BookingTherapistAssignment.objects.filter(booking=self.booking)
        
        # Get all therapists
        therapists = CustomUser.objects.filter(user_type='COMMONSTAFF')
        
        # Check availability for each therapist based on exact time match
        therapist_availability = {}
        booking_time = self.booking.date_time
        
        for therapist in therapists:
            conflicts = BookingTherapistAssignment.objects.filter(
                therapist=therapist,
                booking__date_time=booking_time,  # Exact time match
                booking__status__in=['PENDING', 'CONFIRMED']
            ).exclude(booking=self.booking)
            
            therapist_availability[therapist.id] = not conflicts.exists()
        
        context.update({
            'main_service': main_service,
            'additional_services': additional_services,
            'assignments': assignments,
            'therapist_availability': therapist_availability
        })
        
        return context

class RemoveTherapistAssignmentView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    pass
    # model = BookingTherapist
    
    # def get_success_url(self):
    #     return reverse('booking_detail', kwargs={'pk': self.object.booking.pk})
    
    # def delete(self, request, *args, **kwargs):
    #     therapist_assignment = self.get_object()
    #     booking = therapist_assignment.booking
    #     therapist = therapist_assignment.therapist
        
    #     messages.success(request, f"Removed therapist {therapist.get_full_name()} from booking {booking.booking_id}.")
    #     return super().delete(request, *args, **kwargs)