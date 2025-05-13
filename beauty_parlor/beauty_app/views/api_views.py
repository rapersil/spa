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
            try:
                naive_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
                date_time = timezone.make_aware(naive_datetime)
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DDThh:mm'}, status=400)
            
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Service not found'}, status=404)
    
    service_duration = service.duration
    start_time = date_time
    end_time = start_time + timedelta(minutes=service_duration)

    
    try:
        # Get therapists with this as their primary service
        therapists = CustomUser.objects.filter(
            primary_service=service,
            user_type='COMMONSTAFF'
        )
        
        # Prepare response data
        therapist_data = []
        
        for therapist in therapists:
            # Check if therapist is busy at exactly this time
            busy = BookingTherapistAssignment.objects.filter(
                therapist=therapist,
                # service = service,
                booking__date_time__gte=start_time,
                booking__date_time__lte = end_time,
                # booking__date_time=date_time,  # Exact time match on the booking
                booking__status__in=['PENDING', 'CONFIRMED']
            ).exists()
            
            # Get next available time slot if busy
            next_available = None
            if busy:
                # Find other times when the therapist is available
                upcoming_times = []
                
                # Check hourly slots for the next 24 hours
                for hour in range(1, 25):
                    check_time = date_time + timedelta(hours=hour)
                    
                    # Only consider business hours (8 AM to 8 PM)
                    if 8 <= check_time.hour < 20:
                        time_busy = BookingTherapistAssignment.objects.filter(
                            therapist=therapist,
                            booking__date_time=check_time,
                            booking__status__in=['PENDING', 'CONFIRMED']
                        ).exists()
                        
                        if not time_busy:
                            upcoming_times.append(check_time)
                
                # Return the earliest available time
                if upcoming_times:
                    next_available = upcoming_times[0].strftime('%H:%M')
            
            therapist_data.append({
                'id': therapist.id,
                'name': therapist.get_full_name() or therapist.username,
                'available': not busy,
                'next_available': next_available
            })
        
        return JsonResponse({'therapists': therapist_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# def therapists_for_service(request):
#     """API endpoint to get therapists available for a given service and datetime"""
#     service_id = request.GET.get('service_id')
#     date_time_str = request.GET.get('date_time')
#     booking_id = request.GET.get('booking_id', None)  # Optional - for existing bookings
    
#     if not service_id or not date_time_str:
#         return JsonResponse({'error': 'Missing parameters'}, status=400)
    
#     try:
#         service = Service.objects.get(pk=service_id)
        
#         # Parse the datetime and make it timezone-aware
#         date_time = parse_datetime(date_time_str)
#         if not date_time:
#             return JsonResponse({'error': 'Invalid date format'}, status=400)
        
#         # Get all therapists qualified for this service
#         therapists = CustomUser.objects.filter(
#             Q(primary_service=service) | Q(assigned_services__service=service),
#             user_type__in=['COMMONSTAFF'],
#             is_active=True
#         ).distinct()
        
#         # If no qualified therapists, get all staff
#         if not therapists.exists():
#             therapists = CustomUser.objects.filter(
#                 user_type__in=['COMMONSTAFF'],
#                 is_active=True
#             )
        
#         # Calculate service duration and end time
#         service_duration = service.duration
#         service_end_time = date_time + timedelta(minutes=service_duration)
        
#         # Prepare response data
#         therapist_data = []
        
#         for therapist in therapists:
#             # Check for overlapping assignments
#             query = Q(
#                 booking__therapist_assignments__therapist=therapist,
#                 booking__date_time__lt=service_end_time,
#                 booking__date_time__gt=date_time,
#                 booking__status__in=['PENDING', 'CONFIRMED']
#             )
            
#             # Exclude current booking if provided
#             if booking_id:
#                 query = query & ~Q(booking__id=booking_id)
                
#             conflicts = Booking.objects.filter(query).distinct()
            
#             # Check availability
#             is_available = not conflicts.exists()
            
#             # Get next available time if busy
#             next_available = None
#             if not is_available:
#                 latest_conflict = conflicts.order_by('-date_time').first()
#                 if latest_conflict:
#                     latest_service = latest_conflict.service
#                     end_time = latest_conflict.date_time + timedelta(minutes=latest_service.duration)
#                     next_available = end_time.strftime('%H:%M')
            
#             therapist_data.append({
#                 'id': therapist.id,
#                 'name': therapist.get_full_name() or therapist.username,
#                 'primary_service': therapist.primary_service.name if therapist.primary_service else None,
#                 'available': is_available,
#                 'next_available': next_available,
#                 'warning': not is_available
#             })
        
#         return JsonResponse({
#             'therapists': therapist_data,
#             'service': {
#                 'id': service.id,
#                 'name': service.name,
#                 'duration': service.duration
#             }
#         })
        
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)