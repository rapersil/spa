from datetime import datetime, timedelta, datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView
from django.views.generic.edit import FormView
from django.http import JsonResponse

from beauty_app.forms import TherapistAssignmentForm
from django.contrib import messages
from beauty_app.models import Booking, AdditionalService, CustomUser, Service, BookingTherapistAssignment
from beauty_app.permissions import StaffRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone


class TherapistAssignmentView(LoginRequiredMixin, StaffRequiredMixin, FormView):
    template_name = 'booking/therapist_assignment.html'
    form_class = TherapistAssignmentForm

    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.booking = None

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
            assignment.updated_at = datetime.now()
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
        therapists = CustomUser.objects.filter(user_type='STAFFLEVEL2')

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
    model = BookingTherapistAssignment
    template_name = 'booking/booking_therapist_assignment_confirm_delete.html'

    def get_success_url(self):
        return reverse('booking_detail', kwargs={'pk': self.object.booking.pk})

    def delete(self, request, *args, **kwargs):
        therapist_assignment = self.get_object()
        booking = therapist_assignment.booking
        therapist = therapist_assignment.therapist

        messages.success(request, f"Removed therapist {therapist.get_full_name()} from booking {booking.booking_id}.")
        return super().delete(request, *args, **kwargs)


class TherapistListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """View to list all therapists in the system with enhanced filtering"""
    model = CustomUser
    template_name = 'therapist/therapist_list.html'
    context_object_name = 'therapists'

    def get_queryset(self):
        return CustomUser.objects.filter(
            user_type='STAFFLEVEL2',
            is_active=True
        ).select_related('primary_service').annotate(
            total_bookings=Count('booking_assignments'),
            upcoming_bookings=Count(
                'booking_assignments',
                filter=Q(
                    booking_assignments__booking__status__in=['PENDING', 'CONFIRMED'],
                    booking_assignments__booking__date_time__gt=timezone.now()
                )
            )
        ).order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current timezone-aware datetime for real-time status checking
        current_time = timezone.now()

        # Enhance each therapist with real-time status
        therapists = context['therapists']
        available_count = 0
        busy_count = 0

        for therapist in therapists:
            # Check if therapist has a booking happening right now
            current_booking = BookingTherapistAssignment.objects.filter(
                therapist=therapist,
                booking__status__in=['CONFIRMED'],  # Only confirmed bookings count as "busy"
                booking__date_time__lte=current_time,
                booking__date_time__gt=current_time - timedelta(hours=24)  # Within last 24 hours
            ).select_related('booking__service').first()

            if current_booking:
                # Calculate end time of the booking
                booking_end_time = current_booking.booking.date_time + timedelta(
                    minutes=current_booking.booking.service.duration
                )
                # Check if booking is currently active (compare timezone-aware datetimes)
                therapist.is_currently_busy = current_time <= booking_end_time
                therapist.current_booking = current_booking.booking if therapist.is_currently_busy else None

                if therapist.is_currently_busy:
                    busy_count += 1
                else:
                    available_count += 1
            else:
                therapist.is_currently_busy = False
                therapist.current_booking = None
                available_count += 1

        # Add summary statistics
        total_therapists = len(therapists)
        active_therapists = sum(1 for t in therapists if hasattr(t, 'upcoming_bookings') and t.upcoming_bookings > 0)

        # Get all services for filtering
        services = Service.objects.filter(active=True).order_by('name')

        context.update({
            'total_therapists': total_therapists,
            'active_therapists': active_therapists,
            'available_therapists': available_count,
            'busy_therapists': busy_count,
            'services': services,
        })

        return context


def therapist_detail_api(request, therapist_id):
    """API endpoint to get detailed therapist information for modal"""
    therapist = get_object_or_404(CustomUser, id=therapist_id, user_type='STAFFLEVEL2')

    # Get date range - last 30 days to next 30 days
    start_date = datetime.now().date() - timedelta(days=30)
    end_date = datetime.now().date() + timedelta(days=30)

    # Get therapist statistics
    total_bookings = BookingTherapistAssignment.objects.filter(
        therapist=therapist
    ).count()

    completed_bookings = BookingTherapistAssignment.objects.filter(
        therapist=therapist,
        booking__status='COMPLETED'
    ).count()

    upcoming_bookings = BookingTherapistAssignment.objects.filter(
        therapist=therapist,
        booking__status__in=['PENDING', 'CONFIRMED'],
        booking__date_time__gte=datetime.now()
    ).count()

    # Get recent bookings
    recent_bookings = Booking.objects.filter(
        therapist_assignments__therapist=therapist,
        date_time__date__gte=start_date,
        date_time__date__lte=end_date
    ).select_related('customer', 'service').order_by('-date_time')[:10]

    recent_bookings_data = []
    for booking in recent_bookings:
        recent_bookings_data.append({
            'id': booking.id,
            'booking_id': booking.booking_id,
            'customer_name': f"{booking.customer.first_name} {booking.customer.last_name}",
            'service_name': booking.service.name,
            'date_time': booking.date_time.strftime('%Y-%m-%d %H:%M'),
            'status': booking.get_status_display(),
            'status_class': booking.status.lower(),
        })

    # Calculate total revenue from completed bookings
    total_revenue = 0
    completed_assignments = BookingTherapistAssignment.objects.filter(
        therapist=therapist,
        booking__status='COMPLETED'
    ).select_related('booking__sale')

    for assignment in completed_assignments:
        if hasattr(assignment.booking, 'sale'):
            total_revenue += assignment.booking.sale.payment_amount

    # Get upcoming schedule (next 7 days)
    upcoming_schedule = []
    for i in range(7):
        date = datetime.now().date() + timedelta(days=i)
        day_bookings = Booking.objects.filter(
            therapist_assignments__therapist=therapist,
            date_time__date=date,
            status__in=['PENDING', 'CONFIRMED']
        ).select_related('customer', 'service').order_by('date_time')

        bookings_data = []
        for booking in day_bookings:
            bookings_data.append({
                'booking_id': booking.booking_id,
                'customer_name': f"{booking.customer.first_name} {booking.customer.last_name}",
                'service_name': booking.service.name,
                'time': booking.date_time.strftime('%H:%M'),
                'status': booking.get_status_display(),
            })

        upcoming_schedule.append({
            'date': date.strftime('%Y-%m-%d'),
            'day_name': date.strftime('%A'),
            'bookings': bookings_data,
            'booking_count': len(bookings_data)
        })

    data = {
        'therapist': {
            'id': therapist.id,
            'name': therapist.get_full_name(),
            'username': therapist.username,
            'email': therapist.email,
            'phone': therapist.phone_number,
            'primary_service': therapist.primary_service.name if therapist.primary_service else 'Not specified',
            'profile_picture': therapist.profile_picture.url if therapist.profile_picture else None,
            'date_joined': therapist.date_joined.strftime('%Y-%m-%d'),
        },
        'statistics': {
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'upcoming_bookings': upcoming_bookings,
            'total_revenue': float(total_revenue),
            'completion_rate': round((completed_bookings / total_bookings * 100) if total_bookings > 0 else 0, 1)
        },
        'recent_bookings': recent_bookings_data,
        'upcoming_schedule': upcoming_schedule
    }

    return JsonResponse(data)


def booking_calendar_therapist_view(request):
    """Calendar view organized by therapists instead of days"""
    # Get the date from the query params, default to today
    date_param = request.GET.get('date')
    today = datetime.now().date()

    if date_param:
        try:
            current_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            current_date = today
    else:
        current_date = today

    # Calculate previous and next dates
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)

    # Get all active therapists
    therapists = CustomUser.objects.filter(
        user_type='STAFFLEVEL2',
        is_active=True
    ).select_related('primary_service').order_by('first_name', 'last_name')

    # Get all bookings for the specific date
    bookings = Booking.objects.filter(
        date_time__date=current_date,
        status__in=['PENDING', 'CONFIRMED', 'COMPLETED']
    ).select_related('customer', 'service').prefetch_related('therapist_assignments__therapist')

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

    # Group bookings by therapist
    bookings_by_therapist = {}
    for therapist in therapists:
        bookings_by_therapist[therapist.id] = []

    # Add bookings to their respective therapists
    for booking in bookings:
        # Get primary therapist assignment
        primary_assignment = booking.therapist_assignments.filter(is_primary=True).first()
        if primary_assignment:
            therapist_id = primary_assignment.therapist.id
            if therapist_id in bookings_by_therapist:
                bookings_by_therapist[therapist_id].append(booking)
        else:
            # If no primary assignment, assign to first therapist in the assignment
            first_assignment = booking.therapist_assignments.first()
            if first_assignment:
                therapist_id = first_assignment.therapist.id
                if therapist_id in bookings_by_therapist:
                    bookings_by_therapist[therapist_id].append(booking)

    # Calculate statistics
    total_bookings = bookings.count()
    therapists_with_bookings = sum(1 for bookings_list in bookings_by_therapist.values() if bookings_list)

    context = {
        'current_date': current_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'therapists': therapists,
        'bookings': bookings,
        'bookings_by_therapist': bookings_by_therapist,
        'hours': hours,
        'total_bookings': total_bookings,
        'therapists_with_bookings': therapists_with_bookings,
        'is_today': current_date == today,
    }

    return render(request, 'therapist/booking_calendar_therapist.html', context)


def therapist_schedule_view(request, therapist_id):
    """Individual therapist schedule view with calendar and booking management"""

    # Get the therapist
    therapist = get_object_or_404(CustomUser,
                                  id=therapist_id,
                                  user_type='STAFFLEVEL2',
                                  is_active=True)

    # Get the date from query params, default to today
    date_param = request.GET.get('date')
    weekday_param = request.GET.get('weekday')
    today = timezone.now().date()

    # Handle weekday parameter for direct day selection from dashboard
    if weekday_param is not None:
        try:
            weekday = int(weekday_param)
            days_diff = weekday - today.weekday()
            if days_diff < 0:
                days_diff += 7
            current_date = today + timedelta(days=days_diff)
        except ValueError:
            current_date = today
    elif date_param:
        try:
            current_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            current_date = today
    else:
        current_date = today

    # Get view type (day or week)
    view_type = request.GET.get('view', 'day')

    if view_type == 'day':
        start_date = current_date
        end_date = current_date
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
    else:
        # Week view
        start_date = current_date - timedelta(days=current_date.weekday())
        end_date = start_date + timedelta(days=6)
        prev_date = start_date - timedelta(days=7)
        next_date = start_date + timedelta(days=7)

    # Get bookings for this therapist in the date range
    bookings = Booking.objects.filter(
        therapist_assignments__therapist=therapist,
        date_time__date__range=[start_date, end_date],
        status__in=['PENDING', 'CONFIRMED', 'COMPLETED']
    ).select_related('customer', 'service').prefetch_related('therapist_assignments').order_by('date_time')

    # Hours for the schedule (7 AM to 10 PM)
    hours = list(range(7, 23))

    # Calculate grid positions for bookings
    for booking in bookings:
        booking.end_time = booking.date_time + timedelta(minutes=booking.service.duration)

        # Calculate grid positions (each hour = 8 rows, each row = 7.5 minutes)
        start_minutes = (booking.date_time.hour - 7) * 60 + booking.date_time.minute
        booking.start_row = int(start_minutes / 7.5) + 1

        end_minutes = (booking.end_time.hour - 7) * 60 + booking.end_time.minute
        booking.end_row = int(end_minutes / 7.5) + 1

        # Calculate expected start time
        expected_start = booking.get_expected_start_time()
        wait_minutes = booking.get_wait_time_minutes()

        if wait_minutes > 0:
            expected_start_minutes = (expected_start.hour - 7) * 60 + expected_start.minute
            booking.expected_start_row = int(expected_start_minutes / 7.5) + 1

    # Create date range for week view
    date_range = []
    for i in range(7):
        date_range.append(start_date + timedelta(days=i))

    # Group bookings by day for week view
    bookings_by_day = {}
    for day in date_range:
        bookings_by_day[day] = [b for b in bookings if b.date_time.date() == day]

    # Calculate statistics
    today_bookings = [b for b in bookings if b.date_time.date() == today]
    pending_bookings = [b for b in bookings if b.status == 'PENDING']
    confirmed_bookings = [b for b in bookings if b.status == 'CONFIRMED']
    completed_bookings = [b for b in bookings if b.status == 'COMPLETED']

    # Calculate utilization for the selected period
    total_possible_hours = len(date_range) * 8  # 8 working hours per day
    booked_hours = sum(b.service.duration for b in bookings) / 60  # Convert minutes to hours
    utilization_percentage = (booked_hours / total_possible_hours) * 100 if total_possible_hours > 0 else 0

    # Get upcoming bookings (next 7 days)
    upcoming_bookings = Booking.objects.filter(
        therapist_assignments__therapist=therapist,
        date_time__date__range=[today, today + timedelta(days=7)],
        status__in=['PENDING', 'CONFIRMED']
    ).select_related('customer', 'service').order_by('date_time')[:10]

    context = {
        'therapist': therapist,
        'current_date': current_date,
        'start_date': start_date,
        'end_date': end_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'view_type': view_type,
        'date_range': date_range,
        'bookings': bookings,
        'bookings_by_day': bookings_by_day,
        'hours': hours,
        'is_today': current_date == today,

        # Statistics
        'total_bookings': len(bookings),
        'today_bookings_count': len(today_bookings),
        'pending_count': len(pending_bookings),
        'confirmed_count': len(confirmed_bookings),
        'completed_count': len(completed_bookings),
        'utilization_percentage': round(utilization_percentage, 1),
        'upcoming_bookings': upcoming_bookings,

        # Additional context
        'selected_weekday': int(weekday_param) if weekday_param and weekday_param.isdigit() else None,
        'today': today,
        'current_time': timezone.now(),
    }

    return render(request, 'therapist/therapist_schedule.html', context)
