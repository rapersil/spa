# Add to views/api_views.py
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from beauty_app.models import Booking, CustomUser, Service, ServiceTherapist,BookingTherapistAssignment

def therapists_for_service(request):
    """API endpoint to get therapists available for a given service and datetime"""
    service_id = request.GET.get('service_id')
    date_time_str = request.GET.get('date_time')
    
    if not service_id or not date_time_str:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        service = Service.objects.get(pk=service_id)
        
        # Parse the datetime and make it timezone-aware
        try:
            naive_datetime = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M')
            date_time = timezone.make_aware(naive_datetime)
        except ValueError:
            # Try alternate format if the first one fails
            naive_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
            date_time = timezone.make_aware(naive_datetime)
            
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Service not found'}, status=404)
    
    # Calculate the end time based on service duration
    service_duration = service.duration
    start_time = date_time
    end_time = start_time + timedelta(minutes=service_duration)
    
    # Filter therapists to only include those whose primary service matches the requested service
    therapists = CustomUser.objects.filter(
        user_type='STAFFLEVEL2',
        primary_service_id=service_id
    )
    
    # Prepare response data
    therapist_data = []
    
    for therapist in therapists:
        primary_service = therapist.primary_service.name if hasattr(therapist, 'primary_service') and therapist.primary_service else None
        # Check for overlapping bookings
        overlapping_bookings = BookingTherapistAssignment.objects.filter(
            therapist=therapist,
            booking__status__in=['PENDING', 'CONFIRMED'],
            # The booking overlaps if:
            # (booking starts before our end time) AND (booking ends after our start time)
            booking__date_time__lt=end_time
        ).select_related('booking__service')
        
        # Filter to only include bookings that actually overlap
        conflicting_bookings = []
        for assignment in overlapping_bookings:
            booking = assignment.booking
            booking_end_time = booking.date_time + timedelta(minutes=booking.service.duration)
            if booking_end_time > start_time:
                conflicting_bookings.append({
                    'start': booking.date_time,
                    'end': booking_end_time,
                    'service': booking.service.name
                })
        
        # Sort conflicts by start time
        conflicting_bookings.sort(key=lambda x: x['start'])
        
        # Check if there's a direct conflict with our requested time
        is_available = True
        for conflict in conflicting_bookings:
            if (conflict['start'] <= start_time < conflict['end']) or \
               (conflict['start'] < end_time <= conflict['end']) or \
               (start_time <= conflict['start'] and end_time >= conflict['end']):
                is_available = False
                break
        
        # Find next available time if not available
        next_available = None
        if not is_available and conflicting_bookings:
            # Start checking from the end of the last conflicting appointment
            check_time = max(conflicting_bookings, key=lambda x: x['end'])['end']
            
            # Check for a window from end of last appointment to end of day
            end_of_day = date_time.replace(hour=20, minute=0, second=0, microsecond=0)
            
            while check_time < end_of_day and not next_available:
                potential_end_time = check_time + timedelta(minutes=service_duration)
                is_slot_available = True
                
                # Check if this potential slot conflicts with any booking
                for conflict in conflicting_bookings:
                    if (check_time < conflict['end'] and potential_end_time > conflict['start']):
                        is_slot_available = False
                        # Move check_time to the end of this conflict
                        check_time = conflict['end']
                        break
                
                if is_slot_available:
                    next_available = check_time.strftime('%H:%M')
                    break
                
                # If we couldn't find an available slot, increment by 15 minutes and try again
                check_time += timedelta(minutes=15)
        
        # Create schedule timeline data for the day
        schedule = []
        day_start = date_time.replace(hour=9, minute=0, second=0, microsecond=0)
        day_end = date_time.replace(hour=17, minute=0, second=0, microsecond=0)
        
        current_time = day_start
        while current_time < day_end:
            # Check if this time is in a conflict
            time_status = 'available'
            for conflict in conflicting_bookings:
                conflict_start = conflict['start']
                conflict_end = conflict['end']
                
                if conflict_start <= current_time < conflict_end:
                    time_status = 'booked'
                    break
            
            # Check if this is the requested time
            if current_time == start_time:
                time_status = 'requested'
            
            schedule.append({
                'time': current_time.strftime('%H:%M'),
                'status': time_status
            })
            
            # Move to next 30-minute slot
            current_time += timedelta(minutes=30)
        
        therapist_data.append({
            'id': therapist.id,
            'name': therapist.get_full_name() or therapist.username,
            'available': is_available,
            'next_available': next_available,
            'conflicts': conflicting_bookings,
            'schedule': schedule,
            'primary_service': primary_service
        })
    
    return JsonResponse({'therapists': therapist_data, 'service_duration': service_duration})

# def therapists_for_service(request):
#     """API endpoint to get therapists available for a given service and datetime"""
#     service_id = request.GET.get('service_id')
#     date_time_str = request.GET.get('date_time')
    
#     if not service_id or not date_time_str:
#         return JsonResponse({'error': 'Missing parameters'}, status=400)
    
#     try:
#         service = Service.objects.get(pk=service_id)
        
#         # Parse the datetime and make it timezone-aware
#         try:
#             naive_datetime = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M')
#             date_time = timezone.make_aware(naive_datetime)
#         except ValueError:
#             # Try alternate format if the first one fails
#             naive_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
#             date_time = timezone.make_aware(naive_datetime)
            
#     except Service.DoesNotExist:
#         return JsonResponse({'error': 'Service not found'}, status=404)
    
#     # Calculate the end time based on service duration
#     service_duration = service.duration
#     start_time = date_time
#     end_time = start_time + timedelta(minutes=service_duration)
    
#     # Filter therapists to only include those whose primary service matches the requested service
#     therapists = CustomUser.objects.filter(
#         user_type='STAFFLEVEL2',
#         primary_service_id=service_id
#     )
    
#     # Prepare response data
#     therapist_data = []
    
#     for therapist in therapists:
#         primary_service = therapist.primary_service.name if hasattr(therapist, 'primary_service') and therapist.primary_service else None
#         # Check for overlapping bookings
#         overlapping_bookings = BookingTherapistAssignment.objects.filter(
#             therapist=therapist,
#             booking__status__in=['PENDING', 'CONFIRMED'],
#             # The booking overlaps if:
#             # (booking starts before our end time) AND (booking ends after our start time)
#             booking__date_time__lt=end_time
#         ).select_related('booking__service')
        
#         # Filter to only include bookings that actually overlap
#         conflicting_bookings = []
#         for assignment in overlapping_bookings:
#             booking = assignment.booking
#             booking_end_time = booking.date_time + timedelta(minutes=booking.service.duration)
#             if booking_end_time > start_time:
#                 conflicting_bookings.append({
#                     'start': booking.date_time,
#                     'end': booking_end_time,
#                     'service': booking.service.name
#                 })
        
#         # Sort conflicts by start time
#         conflicting_bookings.sort(key=lambda x: x['start'])
        
#         # Check if there's a direct conflict with our requested time
#         is_available = True
#         for conflict in conflicting_bookings:
#             if (conflict['start'] <= start_time < conflict['end']) or \
#                (conflict['start'] < end_time <= conflict['end']) or \
#                (start_time <= conflict['start'] and end_time >= conflict['end']):
#                 is_available = False
#                 break
        
#         # Find next available time if not available
#         next_available = None
#         if not is_available and conflicting_bookings:
#             # Start checking from the end of the last conflicting appointment
#             check_time = max(conflicting_bookings, key=lambda x: x['end'])['end']
            
#             # Check for a 2-hour window
#             end_of_day = date_time.replace(hour=20, minute=0, second=0, microsecond=0)
            
#             while check_time < end_of_day and not next_available:
#                 potential_end_time = check_time + timedelta(minutes=service_duration)
#                 is_slot_available = True
                
#                 # Check if this potential slot conflicts with any booking
#                 for conflict in conflicting_bookings:
#                     if (check_time < conflict['end'] and potential_end_time > conflict['start']):
#                         is_slot_available = False
#                         # Move check_time to the end of this conflict
#                         check_time = conflict['end']
#                         break
                
#                 if is_slot_available:
#                     next_available = check_time.strftime('%H:%M')
#                     break
                
#                 # If we couldn't find an available slot, increment by 15 minutes and try again
#                 check_time += timedelta(minutes=15)
        
#         # Create schedule timeline data for the day
#         schedule = []
#         day_start = date_time.replace(hour=9, minute=0, second=0, microsecond=0)
#         day_end = date_time.replace(hour=17, minute=0, second=0, microsecond=0)
        
#         current_time = day_start
#         while current_time < day_end:
#             # Check if this time is in a conflict
#             time_status = 'available'
#             for conflict in conflicting_bookings:
#                 conflict_start = conflict['start']
#                 conflict_end = conflict['end']
                
#                 if conflict_start <= current_time < conflict_end:
#                     time_status = 'booked'
#                     break
            
#             # Check if this is the requested time
#             if current_time == start_time:
#                 time_status = 'requested'
            
#             schedule.append({
#                 'time': current_time.strftime('%H:%M'),
#                 'status': time_status
#             })
            
#             # Move to next 30-minute slot
#             current_time += timedelta(minutes=30)
        
#         therapist_data.append({
#             'id': therapist.id,
#             'name': therapist.get_full_name() or therapist.username,
#             'available': is_available,
#             'next_available': next_available,
#             'conflicts': conflicting_bookings,
#             'schedule': schedule,
#             'primary_service': primary_service
#         })
    
#     return JsonResponse({'therapists': therapist_data, 'service_duration': service_duration})
