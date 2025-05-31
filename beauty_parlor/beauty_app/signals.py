from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html

from .models import Booking, BookingTherapistAssignment


@receiver(post_save, sender=Booking)
def check_therapist_assignment(sender, instance, created, **kwargs):
    # Skip if the booking is not in a state that requires a therapist
    if instance.status not in ['CONFIRMED', 'COMPLETED']:
        return

    # Check if this booking already has a therapist assigned
    if instance.therapist is not None:
        return

    # Check if this booking has a therapist assignment
    has_assignment = BookingTherapistAssignment.objects.filter(booking=instance).exists()

    if not has_assignment:
        # Store the booking ID in the session for the context processor to pick up
        from .middleware import _thread_local
        request = getattr(_thread_local, 'request', None)

        if request:
            # Create a list of unassigned bookings if it doesn't exist
            if 'unassigned_bookings' not in request.session:
                request.session['unassigned_bookings'] = []

            # Add this booking to the list if not already there
            booking_info = {
                'id': instance.id,
                'booking_id': instance.booking_id,
                'service': instance.service.name,
                'date_time': instance.date_time.strftime('%Y-%m-%d %H:%M')
            }

            # Convert to list to modify
            unassigned_bookings = request.session.get('unassigned_bookings', [])

            # Check if this booking is already in the list
            booking_ids = [b.get('id') for b in unassigned_bookings]
            if instance.id not in booking_ids:
                unassigned_bookings.append(booking_info)
                request.session['unassigned_bookings'] = unassigned_bookings
                request.session.modified = True

                # Add a message for immediate notification
                assignment_url = reverse('therapist_assignment', kwargs={'pk': instance.pk})
                message = format_html(
                    'Booking #{} requires a therapist assignment. <a href="{}">Assign now</a>',
                    instance.booking_id,
                    assignment_url
                )
                messages.warning(request, message)