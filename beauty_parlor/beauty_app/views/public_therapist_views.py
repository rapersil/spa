from django.views.generic import ListView
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from datetime import datetime, timedelta

from ..models import CustomUser, Booking, BookingTherapistAssignment, Service


class PublicTherapistListView(ListView):
    """Public view to list therapists with limited information"""
    model = CustomUser
    template_name = 'therapist/public_therapists_list.html'
    context_object_name = 'therapists'
    
    def get_queryset(self):
        return CustomUser.objects.filter(
            user_type='STAFFLEVEL2',
            is_active=True
        ).select_related('primary_service').annotate(
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
        
        # Get current datetime for real-time status checking
        current_time = timezone.now()
        
        # Enhance each therapist with real-time status
        therapists = context['therapists']
        for therapist in therapists:
            # Check if therapist has a booking happening right now
            current_booking = BookingTherapistAssignment.objects.filter(
                therapist=therapist,
                booking__status__in=['CONFIRMED'],
                booking__date_time__lte=current_time,
                booking__date_time__gt=current_time - timedelta(hours=24)
            ).select_related('booking__service').first()
            
            if current_booking:
                # Calculate end time of the booking
                booking_end_time = current_booking.booking.date_time + timedelta(
                    minutes=current_booking.booking.service.duration
                )
                # Check if booking is currently active
                therapist.is_currently_busy = current_time <= booking_end_time
            else:
                therapist.is_currently_busy = False
        
        # Add summary statistics
        total_therapists = len(therapists)
        currently_busy = sum(1 for t in therapists if getattr(t, 'is_currently_busy', False))
        
        # Get all services for filtering
        services = Service.objects.filter(active=True).order_by('name')
        
        context.update({
            'total_therapists': total_therapists,
            'currently_busy': currently_busy,
            'available_now': total_therapists - currently_busy,
            'services': services,
        })
        
        return context


def public_therapist_detail_api(request, therapist_id):
    """API endpoint for public therapist details (limited information)"""
    therapist = get_object_or_404(CustomUser, id=therapist_id, user_type='STAFFLEVEL2', is_active=True)
    
    # Get upcoming schedule (next 7 days only)
    upcoming_schedule = []
    for i in range(7):
        date = timezone.now().date() + timedelta(days=i)
        day_bookings = Booking.objects.filter(
            therapist_assignments__therapist=therapist,
            date_time__date=date,
            status__in=['PENDING', 'CONFIRMED']
        ).order_by('date_time')
        
        # Only show time slots as busy/available, not customer details
        time_slots = []
        for booking in day_bookings:
            time_slots.append({
                'start_time': booking.date_time.strftime('%H:%M'),
                'end_time': (booking.date_time + timedelta(minutes=booking.service.duration)).strftime('%H:%M'),
                'service_name': booking.service.name,
                'status': 'booked'
            })
        
        upcoming_schedule.append({
            'date': date.strftime('%Y-%m-%d'),
            'day_name': date.strftime('%A'),
            'time_slots': time_slots,
            'available_slots': 8 - len(time_slots)  # Assuming 8 working hours
        })
    
    # Get specialties and services this therapist can provide
    therapist_services = [therapist.primary_service] if therapist.primary_service else []
    
    data = {
        'therapist': {
            'id': therapist.id,
            'name': therapist.get_full_name(),
            'primary_service': therapist.primary_service.name if therapist.primary_service else 'Beauty Therapist',
            'profile_picture': therapist.profile_picture.url if therapist.profile_picture else None,
            'experience_since': therapist.date_joined.strftime('%Y'),
        },
        'services': [
            {
                'name': service.name,
                'description': service.description,
                'duration': service.duration,
                'price': float(service.price)
            } for service in therapist_services
        ],
        'upcoming_schedule': upcoming_schedule,
        'availability_summary': {
            'next_available': get_next_available_slot(therapist),
            'avg_daily_availability': calculate_avg_availability(upcoming_schedule)
        }
    }
    
    return JsonResponse(data)


def get_next_available_slot(therapist):
    """Find the next available booking slot for a therapist"""
    current_time = timezone.now()
    
    # Check next 7 days for availability
    for i in range(7):
        check_date = current_time.date() + timedelta(days=i)
        start_time = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
        if i > 0:
            start_time = start_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=i)
        
        # Get bookings for this day
        day_bookings = Booking.objects.filter(
            therapist_assignments__therapist=therapist,
            date_time__date=check_date,
            status__in=['PENDING', 'CONFIRMED']
        ).order_by('date_time')
        
        # Find gaps in schedule
        if not day_bookings.exists():
            return start_time.strftime('%Y-%m-%d %H:%M')
        
        # Check for gaps between bookings
        prev_end = start_time
        for booking in day_bookings:
            if booking.date_time >= prev_end + timedelta(hours=1):  # 1 hour minimum gap
                return prev_end.strftime('%Y-%m-%d %H:%M')
            prev_end = booking.date_time + timedelta(minutes=booking.service.duration)
        
        # Check for availability after last booking
        if prev_end.hour < 17:  # Before 5 PM
            return prev_end.strftime('%Y-%m-%d %H:%M')
    
    return "No availability in next 7 days"


def calculate_avg_availability(schedule):
    """Calculate average daily availability percentage"""
    total_slots = len(schedule) * 8  # 8 hours per day
    booked_slots = sum(len(day['time_slots']) for day in schedule)
    availability_percentage = ((total_slots - booked_slots) / total_slots) * 100
    return round(availability_percentage, 1)

def public_booking_calendar_therapist_view(request):
    """Public therapist calendar view with limited information - updated to match internal view functionality"""
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
    
    # Get all bookings for the specific date (including all statuses like internal view)
    bookings = Booking.objects.filter(
        date_time__date=current_date,
        status__in=['PENDING', 'CONFIRMED', 'COMPLETED']  # Match internal view statuses
    ).select_related('customer', 'service').prefetch_related('therapist_assignments__therapist')
    
    # Extended hours from 7 AM to 10 PM (match internal view)
    hours = list(range(7, 23))  # 7 AM to 10 PM
    
    # Calculate properties for each booking (including expected start times)
    for booking in bookings:
        # Calculate end time
        booking.end_time = booking.date_time + timedelta(minutes=booking.service.duration)
        
        # Calculate grid position (each hour = 8 grid rows, each row = 7.5 minutes)
        start_minutes = (booking.date_time.hour - 7) * 60 + booking.date_time.minute  # Changed from -8 to -7
        booking.start_row = int(start_minutes / 7.5) + 1
        
        # End time grid position
        end_minutes = (booking.end_time.hour - 7) * 60 + booking.end_time.minute  # Changed from -8 to -7
        booking.end_row = int(end_minutes / 7.5) + 1
        
        # Calculate expected start time for calendar display (match internal view)
        expected_start = booking.get_expected_start_time()
        wait_minutes = booking.get_wait_time_minutes()
        
        # If there's a delay, calculate expected start position
        if wait_minutes > 0:
            expected_start_minutes = (expected_start.hour - 7) * 60 + expected_start.minute  # Changed from -8 to -7
            booking.expected_start_row = int(expected_start_minutes / 7.5) + 1
        
        # Anonymize booking for public view (keep this for public display)
        booking.anonymous = True
    
    # Group bookings by therapist (use same logic as internal view)
    bookings_by_therapist = {}
    for therapist in therapists:
        bookings_by_therapist[therapist.id] = []
    
    # Add bookings to their respective therapists (match internal view logic)
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
    
    # Calculate statistics (match internal view)
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
        'is_today': current_date == today,  # Add is_today flag like internal view
        'is_public_view': True,  # Keep this flag to distinguish public view
        'selected_weekday': int(weekday_param) if weekday_param and weekday_param.isdigit() else None  # Add weekday param
    }
    
    return render(request, 'therapist/public_booking_calendar_therapist.html', context)