# beauty_app/views/booking_views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from ..models import Booking, BookingTherapistAssignment, Customer, Service, CustomUser, AdditionalService
from ..forms import BookingForm, AdminBookingForm, BookingSearchForm
from ..permissions import StaffRequiredMixin, AdminRequiredMixin
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta
from decimal import Decimal
import json


class BookingListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Booking
    template_name = 'booking/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Booking.objects.all().order_by('-date_time')
        
        # Get filter parameters from form
        form = BookingSearchForm(self.request.GET)
        if form.is_valid():
            query = form.cleaned_data.get('query')
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            status = form.cleaned_data.get('status')
            
            # Apply filters if provided
            if query:
                queryset = queryset.filter(
                    Q(customer__first_name__icontains=query) |
                    Q(customer__last_name__icontains=query) |
                    Q(service__name__icontains=query) |
                    Q(booking_id__iexact=query)
                )
            
            if start_date:
                queryset = queryset.filter(date_time__date__gte=start_date)
                
            if end_date:
                queryset = queryset.filter(date_time__date__lte=end_date)
                
            if status:
                queryset = queryset.filter(status=status)
                
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = BookingSearchForm(self.request.GET)
        context['today'] = timezone.now().date()
        context['current_time'] = timezone.now()
        context['status_choices'] = Booking.STATUS_CHOICES
        return context

class BookingDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Booking
    template_name = 'booking/booking_detail.html'
    context_object_name = 'booking'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.get_object()
        
        # Set service_discount in context
        context['service_discount'] = booking.service_discount
        
        # Add additional services to context
        context['additional_services'] = AdditionalService.objects.filter(booking=booking)
        
        
        # Calculate total price (main service + additional services)
        main_service_price = booking.get_final_price()
        additional_services_total = sum(service.final_price for service in context['additional_services'])
        context['total_price'] = main_service_price + additional_services_total

        context['service_assignments'] = BookingTherapistAssignment.objects.filter(booking=booking)

        context['current_time'] = timezone.now()
        

        
        return context
    


import logging


# Set up logging for debugging
logger = logging.getLogger(__name__)

class BookingCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Booking
    template_name = 'booking/booking_form.html'
    success_url = reverse_lazy('booking_list')
    
    def get_form_class(self):
        # Admin users get the form with discount option
        if self.request.user.user_type in ['ADMIN', 'SUPERADMIN']:
            return AdminBookingForm
        # Staff users get the standard form
        return BookingForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        booking = form.instance
        booking.created_by = self.request.user
        booking.updated_by = self.request.user
        
        # Check for active service discounts at the time of booking
        active_discounts = booking.service.discount_set.filter(
            start_date__lte=booking.date_time,
            end_date__gte=booking.date_time
        ).order_by('-percentage')  # Get highest discount if multiple exist
        
        # Apply service discount if available
        if active_discounts.exists():
            booking.service_discount = active_discounts.first()
        
        messages.success(self.request, "Booking created successfully.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # If customer_id is in GET parameters, pre-select customer
        customer_id = self.request.GET.get('customer_id')
        if customer_id:
            customer = get_object_or_404(Customer, pk=customer_id)
            context['selected_customer'] = customer
            
        # If service_id is in GET parameters, pre-select service
        service_id = self.request.GET.get('service_id')
        if service_id:
            service = get_object_or_404(Service, pk=service_id)
            context['selected_service'] = service
            
        return context
# class BookingUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
#     model = Booking
#     template_name = 'booking/booking_form.html'
    
#     def get_form_class(self):
#         # Admin users get the form with discount option
#         if self.request.user.user_type in ['ADMIN', 'SUPERADMIN']:
#             return AdminBookingForm
#         # Staff users get the standard form
#         return BookingForm
    
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['user'] = self.request.user
#         return kwargs
    
#     def form_valid(self, form):
#         # Get the form's cleaned data
#         service = form.cleaned_data.get('service')
#         date_time = form.cleaned_data.get('date_time')
#         additional_services = form.cleaned_data.get('additional_services', [])
        
#         # First save the form to get the instance
#         response = super().form_valid(form)
        
#         # Now work with the saved instance
#         booking = self.object
#         booking.updated_by = self.request.user
        
#         # Check for active service discounts at the booking time
#         active_discounts = service.discount_set.filter(
#             start_date__lte=date_time,
#             end_date__gte=date_time
#         ).order_by('-percentage')  # Get highest discount if multiple exist
        
#         # Apply service discount if available, otherwise set to None
#         if active_discounts.exists():
#             booking.service_discount = active_discounts.first()
#         else:
#             booking.service_discount = None
            
#         # Save the booking again with updated service_discount
#         booking.save(update_fields=['service_discount', 'updated_by'])
        
#         # Remove existing additional services
#         AdditionalService.objects.filter(booking=booking).delete()
        
#         # Add new additional services
#         if additional_services:
#             # Process each additional service
#             for service in additional_services:
#                 # Check for active discounts
#                 service_discount_percent = 0
#                 active_service_discounts = service.discount_set.filter(
#                     start_date__lte=booking.date_time,
#                     end_date__gte=booking.date_time
#                 ).order_by('-percentage')
                
#                 if active_service_discounts.exists():
#                     service_discount_percent = active_service_discounts.first().percentage
                
#                 # Calculate final price
#                 regular_price = service.price
#                 if service_discount_percent > 0:
#                     discount_amount = regular_price * (service_discount_percent / 100)
#                     final_price = regular_price - discount_amount
#                 else:
#                     final_price = regular_price
                
#                 # Create additional service record
#                 AdditionalService.objects.create(
#                     booking=booking,
#                     sale=None,  # Not associated with a sale yet
#                     name=service.name,
#                     description=service.description,
#                     regular_price=regular_price,
#                     discount_percentage=service_discount_percent,
#                     final_price=final_price,
#                     created_by=self.request.user
#                 )
        
#         messages.success(self.request, "Booking updated successfully.")
#         return response
    
#     def get_success_url(self):
#         return reverse_lazy('booking_detail', kwargs={'pk': self.object.pk})
# class BookingUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
#     model = Booking
#     template_name = 'booking/booking_form.html'
    
#     def get_form_class(self):
#         # Admin users get the form with discount option
#         if self.request.user.user_type in ['ADMIN', 'SUPERADMIN']:
#             return AdminBookingForm
#         # Staff users get the standard form
#         return BookingForm
    
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['user'] = self.request.user
#         return kwargs
    
#     def form_valid(self, form):
#         # Get the form's cleaned data
#         service = form.cleaned_data.get('service')
#         date_time = form.cleaned_data.get('date_time')
        
#         # First save the form to get the instance
#         response = super().form_valid(form)
        
#         # Now work with the saved instance
#         booking = self.object
#         booking.updated_by = self.request.user
        
#         # Check for active service discounts at the booking time
#         active_discounts = service.discount_set.filter(
#             start_date__lte=date_time,
#             end_date__gte=date_time
#         ).order_by('-percentage')  # Get highest discount if multiple exist
        
#         # Apply service discount if available, otherwise set to None
#         if active_discounts.exists():
#             booking.service_discount = active_discounts.first()
#         else:
#             booking.service_discount = None
            
#         # Save the booking again with updated service_discount
#         booking.save(update_fields=['service_discount', 'updated_by'])
        
#         # Remove existing additional services
#         AdditionalService.objects.filter(booking=booking, sale__isnull=True).delete()
        
#         # Parse additional services from JSON
#         additional_services_json = self.request.POST.get('additional_services', '[]')
#         try:
#             additional_services_data = json.loads(additional_services_json)
#         except json.JSONDecodeError:
#             additional_services_data = []
        
#         # Create additional service records
#         if additional_services_data:
#             for service_data in additional_services_data:
#                 # Create additional service record
#                 AdditionalService.objects.create(
#                     booking=booking,
#                     sale=None,  # Not associated with a sale yet
#                     name=service_data.get('name', ''),
#                     description='',  # Optional description
#                     regular_price=Decimal(str(service_data.get('regularPrice', 0))),
#                     discount_percentage=Decimal(str(service_data.get('discountPercentage', 0))),
#                     final_price=Decimal(str(service_data.get('finalPrice', 0))),
#                     created_by=self.request.user
#                 )
        
#         messages.success(self.request, "Booking updated successfully.")
#         return response
    
#     def get_success_url(self):
#         return reverse_lazy('booking_detail', kwargs={'pk': self.object.pk})
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
        
#         # Get available services for selection, excluding the main service
#         form = context['form']
#         context['available_services'] = form.get_available_services_with_discounts()
        
#         # Add existing additional services for initialization
#         if self.object:
#             context['existing_additional_services'] = self.object.additional_services.all()
        
#         return context

class BookingUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Booking
    template_name = 'booking/booking_form.html'
    
    def get_form_class(self):
        # Admin users get the form with discount option
        if self.request.user.user_type in ['ADMIN', 'SUPERADMIN']:
            return AdminBookingForm
        # Staff users get the standard form
        return BookingForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Check if a new time was suggested from therapist assignment
        new_time = self.request.GET.get('new_time')
        if new_time:
            try:
                # Parse the new time and set it as initial value
                from datetime import datetime
                from django.utils import timezone
                
                # Handle different formats depending on what's passed
                if 'T' in new_time:
                    # ISO format: 2025-05-17T14:30
                    new_datetime = datetime.strptime(new_time, '%Y-%m-%dT%H:%M')
                else:
                    # Time only: 14:30
                    current_date = self.object.date_time.date()
                    time_parts = new_time.split(':')
                    new_datetime = datetime.combine(
                        current_date,
                        datetime.time(int(time_parts[0]), int(time_parts[1]))
                    )
                
                # Make it timezone aware
                new_datetime = timezone.make_aware(new_datetime)
                initial['date_time'] = new_datetime
                
                # Add a message to explain the time change
                messages.info(self.request, 
                    "The booking time has been updated to match therapist availability. "
                    "Review and save the changes to confirm.")
            except (ValueError, TypeError, IndexError) as e:
                # If time format is invalid, log it but continue
                print(f"Error parsing time update: {e}")
                pass
                
        return initial
    
    def form_valid(self, form):
        # Get the form's cleaned data
        service = form.cleaned_data.get('service')
        date_time = form.cleaned_data.get('date_time')
        
        # First save the form to get the instance
        response = super().form_valid(form)
        
        # Now work with the saved instance
        booking = self.object
        booking.updated_by = self.request.user
        
        # Check for active service discounts at the booking time
        active_discounts = service.discount_set.filter(
            start_date__lte=date_time,
            end_date__gte=date_time
        ).order_by('-percentage')  # Get highest discount if multiple exist
        
        # Apply service discount if available, otherwise set to None
        if active_discounts.exists():
            booking.service_discount = active_discounts.first()
        else:
            booking.service_discount = None
            
        # Save the booking again with updated service_discount
        booking.save(update_fields=['service_discount', 'updated_by'])
        
        # Remove existing additional services
        AdditionalService.objects.filter(booking=booking, sale__isnull=True).delete()
        
        # Parse additional services from JSON
        additional_services_json = self.request.POST.get('additional_services', '[]')
        try:
            additional_services_data = json.loads(additional_services_json)
        except json.JSONDecodeError:
            additional_services_data = []
        
        # Create additional service records
        if additional_services_data:
            for service_data in additional_services_data:
                # Create additional service record
                AdditionalService.objects.create(
                    booking=booking,
                    sale=None,  # Not associated with a sale yet
                    name=service_data.get('name', ''),
                    description='',  # Optional description
                    regular_price=Decimal(str(service_data.get('regularPrice', 0))),
                    discount_percentage=Decimal(str(service_data.get('discountPercentage', 0))),
                    final_price=Decimal(str(service_data.get('finalPrice', 0))),
                    created_by=self.request.user
                )
        
        messages.success(self.request, "Booking updated successfully.")
        return response
    
    def get_success_url(self):
        return reverse_lazy('booking_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get available services for selection, excluding the main service
        form = context['form']
        context['available_services'] = form.get_available_services_with_discounts()
        
        # Add existing additional services for initialization
        if self.object:
            context['existing_additional_services'] = self.object.additional_services.all()
        
        return context

class BookingDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Booking
    template_name = 'booking/booking_confirm_delete.html'
    success_url = reverse_lazy('booking_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Booking deleted successfully.")
        return super().delete(request, *args, **kwargs)

class BookingStatusUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Booking
    fields = ['status']
    http_method_names = ['post']
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"Booking status updated to {form.instance.get_status_display()}.")
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirect back to the page we came from, or booking list
        next_url = self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('booking_list')
    





from django.views.generic import TemplateView

class BookingPrintView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'booking/booking_receipt.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking_id = self.kwargs.get('pk')
        booking = get_object_or_404(Booking, pk=booking_id)
        
        context['booking'] = booking
        
        # Use the stored service discount from the booking
        context['service_discount'] = booking.service_discount
        
        # Calculate discount amounts
        if booking.service_discount:
            service_discount_amount = booking.service.price * (booking.service_discount.percentage / 100)
            context['service_discount_amount'] = service_discount_amount
            
            if booking.custom_discount > 0:
                # Custom discount applies to price after service discount
                price_after_service_discount = booking.service.price - service_discount_amount
                custom_discount_amount = price_after_service_discount * (booking.custom_discount / 100)
                context['custom_discount_amount'] = custom_discount_amount
        elif booking.custom_discount > 0:
            # Only custom discount
            custom_discount_amount = booking.service.price * (booking.custom_discount / 100)
            context['custom_discount_amount'] = custom_discount_amount
            
        # Add expected start time calculation
        expected_start_time = booking.get_expected_start_time()
        wait_time_minutes = booking.get_wait_time_minutes()
        context['expected_start_time'] = expected_start_time
        context['wait_time_minutes'] = wait_time_minutes
        
        # IMPROVED QR CODE GENERATION WITH WAIT TIME INFO
        # Create a well-structured text format for QR code scanners
        verification_text = (
            f"ID:{booking.booking_id}\n"
            f"Customer:{booking.customer.first_name} {booking.customer.last_name}\n"
            f"Service:{booking.service.name}\n"
            f"Date:{booking.date_time.strftime('%Y-%m-%d')}\n"
            f"Scheduled:{booking.date_time.strftime('%H:%M')}\n"
        )
        
        # Add expected start time and wait time if applicable
        if wait_time_minutes > 0 and expected_start_time:
            verification_text += f"ExpectedStart:{expected_start_time.strftime('%H:%M')}\n"
            verification_text += f"WaitTime:{wait_time_minutes} minutes\n"
        
        verification_text += f"Duration:{booking.service.duration} minutes\n"
        verification_text += f"Amount:GHS{booking.get_final_price()}\n"
        verification_text += f"Status:{booking.get_status_display()}\n"
        
        # Generate QR code with higher error correction level
        qr = qrcode.QRCode(
            version=None,  # Auto-determine version based on data size
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Higher error correction
            box_size=10,
            border=4,
        )
        qr.add_data(verification_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 string for embedding in HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        context['qr_code'] = img_str
        
        return context
    



def booking_calendar_view(request):
    # Get the date from the query params, default to today
    date_param = request.GET.get('date')
    weekday_param = request.GET.get('weekday')  # Add weekday selection parameter
    today = timezone.now().date()
    
    # Handle weekday parameter for direct day selection from dashboard
    if weekday_param is not None:
        try:
            weekday = int(weekday_param)
            # Calculate the date of the selected weekday in the current week
            days_diff = weekday - today.weekday()
            if days_diff < 0:  # If the day has passed this week
                days_diff += 7
            current_date = today + timedelta(days=days_diff)
        except ValueError:
            current_date = today
    # Handle explicit date parameter
    elif date_param:
        try:
            current_date = datetime.strptime(date_param, '%Y-%m-%d').date()  # Fixed typo in date format
        except ValueError:
            current_date = today
    else:
        current_date = today
    
    # Get the view type (day or week)
    view_type = request.GET.get('view', 'day' if weekday_param else 'week')  # Default to day view if weekday specified
    
    if view_type == 'day':
        # Day view - single day
        start_date = current_date
        end_date = current_date
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
    else:
        # Week view - show the whole week
        # Calculate the start of the week (Monday)
        start_date = current_date - timedelta(days=current_date.weekday())
        # Calculate the end of the week (Sunday)
        end_date = start_date + timedelta(days=6)
        prev_date = start_date - timedelta(days=7)
        next_date = start_date + timedelta(days=7)
    
    # Get all bookings for the date range
    bookings = Booking.objects.filter(
        date_time__date__range=[start_date, end_date],
        status__in=['PENDING', 'CONFIRMED', 'COMPLETED']
    ).order_by('date_time')
    
    # Extended hours from 7 AM to 10 PM
    hours = list(range(7, 23))  # 7 AM to 10 PM
    
    # Calculate properties for each booking
    for booking in bookings:
        # Calculate end time
        booking.end_time = booking.date_time + timedelta(minutes=booking.service.duration)
        
        # Calculate grid position (each hour = 8 grid rows, each row = 7.5 minutes)
        start_minutes = (booking.date_time.hour - 7) * 60 + booking.date_time.minute
        booking.start_row = int(start_minutes / 7.5) + 1  # +1 for 1-based grid
        
        # End time grid position
        end_minutes = (booking.end_time.hour - 7) * 60 + booking.end_time.minute
        booking.end_row = int(end_minutes / 7.5) + 1
        
        # Calculate expected start time for calendar display
        expected_start = booking.get_expected_start_time()
        wait_minutes = booking.get_wait_time_minutes()
        
        # If there's a delay, calculate expected start position
        if wait_minutes > 0:
            expected_start_minutes = (expected_start.hour - 7) * 60 + expected_start.minute
            booking.expected_start_row = int(expected_start_minutes / 7.5) + 1
            
        # Add day of week for positioning in week view
        booking.day_of_week = booking.date_time.weekday()
    
    # Create a list of dates for the week
    date_range = []
    for i in range(7):
        date_range.append(start_date + timedelta(days=i))
    
    # Group bookings by day
    bookings_by_day = {}
    for day in date_range:
        bookings_by_day[day] = [b for b in bookings if b.date_time.date() == day]
    
    # Get all staff (created_by users) for staff grouping
    staffs = CustomUser.objects.filter(
        user_type__in=['STAFF', 'ADMIN', 'SUPERADMIN']
    ).distinct()
    
    # Group bookings by staff
    bookings_by_staff = {}
    for staff in staffs:
        bookings_by_staff[staff.id] = []
        
    for booking in bookings:
        if booking.created_by:
            staff_id = booking.created_by.id
            if staff_id in bookings_by_staff:
                bookings_by_staff[staff_id].append(booking)
    
    # Day labels for week view
    day_labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    context = {
        'current_date': current_date,
        'start_date': start_date,
        'end_date': end_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'view_type': view_type,
        'date_range': date_range,
        'day_labels': day_labels,
        'bookings': bookings,
        'bookings_by_day': bookings_by_day,
        'hours': hours,
        'staffs': staffs,
        'bookings_by_staff': bookings_by_staff,
        'selected_weekday': int(weekday_param) if weekday_param and weekday_param.isdigit() else None
    }
    
    return render(request, 'booking/booking_calendar.html', context)



def public_booking_calendar_view(request):
    """A public-facing calendar view showing booked time slots without personal details"""
    # Get the date from the query params, default to today
    date_param = request.GET.get('date')
    weekday_param = request.GET.get('weekday')  # Add weekday selection parameter
    today = timezone.now().date()
    
    # Handle weekday parameter for direct day selection
    if weekday_param is not None:
        try:
            weekday = int(weekday_param)
            # Calculate the date of the selected weekday in the current week
            days_diff = weekday - today.weekday()
            if days_diff < 0:  # If the day has passed this week
                days_diff += 7
            current_date = today + timedelta(days=days_diff)
        except ValueError:
            current_date = today
    # Handle explicit date parameter
    elif date_param:
        try:
            current_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            current_date = today
    else:
        current_date = today
    
    # Get the view type (day or week)
    view_type = request.GET.get('view', 'day' if weekday_param else 'week')  # Default to day view if weekday specified
    
    if view_type == 'day':
        # Day view - single day
        start_date = current_date
        end_date = current_date
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
    else:
        # Week view - show the whole week
        # Calculate the start of the week (Monday)
        start_date = current_date - timedelta(days=current_date.weekday())
        # Calculate the end of the week (Sunday)
        end_date = start_date + timedelta(days=6)
        prev_date = start_date - timedelta(days=7)
        next_date = start_date + timedelta(days=7)
    
    # Get all bookings for the date range, but only those with status CONFIRMED or PENDING
    bookings = Booking.objects.filter(
        date_time__date__range=[start_date, end_date],
        status__in=['PENDING', 'CONFIRMED']
    ).order_by('date_time')
    
    # Anonymize the bookings - replace customer names with "Reserved"
    for booking in bookings:
        # Hide customer information
        booking.anonymous = True
        # Calculate end time
        booking.end_time = booking.date_time + timedelta(minutes=booking.service.duration)
        
        # Calculate grid position (each hour = 8 grid rows, each row = 7.5 minutes)
        start_minutes = (booking.date_time.hour - 7) * 60 + booking.date_time.minute
        booking.start_row = int(start_minutes / 7.5) + 1  # +1 for 1-based grid
        
        # End time grid position
        end_minutes = (booking.end_time.hour - 7) * 60 + booking.end_time.minute
        booking.end_row = int(end_minutes / 7.5) + 1
        
        # Add day of week for positioning in week view
        booking.day_of_week = booking.date_time.weekday()
    
    # Create a list of dates for the week
    date_range = []
    for i in range(7):
        date_range.append(start_date + timedelta(days=i))
    
    # Group bookings by day
    bookings_by_day = {}
    for day in date_range:
        bookings_by_day[day] = [b for b in bookings if b.date_time.date() == day]
    
    # Extended hours from 7 AM to 10 PM
    hours = list(range(7, 23))  # 7 AM to 10 PM
    
    # Get active services for the sidebar
    active_services = Service.objects.filter(active=True)
    
    # Day labels for week view
    day_labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    context = {
        'current_date': current_date,
        'start_date': start_date,
        'end_date': end_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'view_type': view_type,
        'date_range': date_range,
        'day_labels': day_labels,
        'bookings': bookings,
        'bookings_by_day': bookings_by_day,
        'hours': hours,
        'active_services': active_services,
        'selected_weekday': int(weekday_param) if weekday_param and weekday_param.isdigit() else None
    }
    
    return render(request, 'booking/public_booking_calendar.html', context)