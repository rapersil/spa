from django.views.generic import View, ListView, DetailView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import Q

from ..models import Customer, Service, BookingRequest, Booking, CustomUser
from ..booking_request_forms import (
    CustomerSelectionForm, ServiceSelectionForm, 
    AdditionalServicesForm, BookingRequestForm
)
from ..permissions import StaffRequiredMixin, AdminRequiredMixin

class PublicBookingRequestCreateView(View):
    """Multi-step form for public users to create booking requests"""
    
    def get(self, request, *args, **kwargs):
        step = kwargs.get('step', 1)
        
        # Check if we have session data from previous steps
        form_data = request.session.get('booking_request_form_data', {})
        
        if step == 1:
            # Step 1: Customer information
            form = CustomerSelectionForm(initial=form_data.get('step1', {}))
            return render(request, 'booking/public_booking_request_step1.html', {'form': form})
        
        elif step == 2:
            # Step 2: Service selection
            # Only allow proceeding to step 2 if step 1 is complete
            if not form_data.get('step1'):
                messages.error(request, "Please complete step 1 first.")
                return redirect('public_booking_request_create', step=1)
                
            form = ServiceSelectionForm(initial=form_data.get('step2', {}))
            return render(request, 'booking/public_booking_request_step2.html', {'form': form})
        
        elif step == 3:
            # Step 3: Additional services
            # Only allow proceeding to step 3 if steps 1 and 2 are complete
            if not form_data.get('step1') or not form_data.get('step2'):
                messages.error(request, "Please complete previous steps first.")
                return redirect('public_booking_request_create', step=1)
                
            # Get the main service selected in step 2
            service_id = form_data.get('step2', {}).get('service')
            if service_id:
                main_service = get_object_or_404(Service, pk=service_id)
                form = AdditionalServicesForm(main_service=main_service, initial=form_data.get('step3', {}))
                return render(request, 'booking/public_booking_request_step3.html', {
                    'form': form,
                    'main_service': main_service
                })
            else:
                messages.error(request, "Please select a service first.")
                return redirect('public_booking_request_create', step=2)
        
        elif step == 4:
            # Step 4: Review and confirm
            # Only allow proceeding to step 4 if all previous steps are complete
            if not form_data.get('step1') or not form_data.get('step2'):
                messages.error(request, "Please complete all previous steps first.")
                return redirect('public_booking_request_create', step=1)
                
            # Get data from previous steps
            step1_data = form_data.get('step1', {})
            step2_data = form_data.get('step2', {})
            step3_data = form_data.get('step3', {})
            
            # Get customer information
            customer_choice = step1_data.get('customer_choice')
            customer = None
            customer_display_data = {}
            
            if customer_choice == 'existing':
                # Get customer ID for existing customers
                customer_id = step1_data.get('existing_customer_id')
                if customer_id:
                    try:
                        customer = get_object_or_404(Customer, pk=customer_id)
                        is_new_customer = False
                        
                        # Prepare customer data for display
                        customer_display_data = {
                            'first_name': customer.first_name,
                            'last_name': customer.last_name,
                            'phone': customer.phone,
                            'email': customer.email,
                            'address': customer.address,
                            'customer_id': customer.id
                        }
                    except Customer.DoesNotExist:
                        messages.error(request, "Customer not found. Please start over.")
                        return redirect('public_booking_request_create', step=1)
                else:
                    # Use the customer data we stored in step 1 if the customer object can't be retrieved
                    customer_display_data = step1_data.get('customer_data', {})
                    is_new_customer = False
            else:
                # For new customers, use the form data directly
                is_new_customer = True
                customer_display_data = {
                    'first_name': step1_data.get('first_name', ''),
                    'last_name': step1_data.get('last_name', ''),
                    'phone': step1_data.get('phone', ''),
                    'email': step1_data.get('email', ''),  # This should be 'email' not 'email_new' as we rename it in the view
                    'address': step1_data.get('address', '')

                }
            
            # Get service information (convert ID to object if needed)
            service_id = step2_data.get('service')
            service = get_object_or_404(Service, pk=service_id) if service_id else None
            
            # Get date_time (handle string-to-datetime conversion if needed)
            date_time = step2_data.get('date_time')
            if isinstance(date_time, str):
                try:
                    from dateutil import parser
                    date_time = parser.parse(date_time)
                except:
                    pass
            
            # Get additional services
            additional_service_ids = step3_data.get('selected_services', [])
            additional_services = Service.objects.filter(pk__in=additional_service_ids)
            
            # Get notes
            notes = step3_data.get('notes', '')
            total_price = service.price if service else 0
            for additional_service in additional_services:
                total_price += additional_service.price
            
            return render(request, 'booking/public_booking_request_step4.html', {
                'customer': customer,
                'is_new_customer': is_new_customer,
                'customer_data': customer_display_data,  # Use our new prepared display data
                'service': service,
                'date_time': date_time,
                'additional_services': additional_services,
                'notes': notes,
                'customer_id': customer.id if customer else None,
                'total_price': total_price,
            })
    
    
    def post(self, request, *args, **kwargs):
        step = kwargs.get('step', 1)
        
        # Get existing form data from session
        form_data = request.session.get('booking_request_form_data', {})
        
        if step == 1:
            # Process step 1: Customer information
            form = CustomerSelectionForm(request.POST)
            
            if form.is_valid():
                # Create a copy of cleaned_data to modify
                cleaned_data = form.cleaned_data.copy()
                
                # Replace the Customer object with just its ID if present
                if 'existing_customer' in cleaned_data and cleaned_data['existing_customer'] is not None:
                    customer_obj = cleaned_data['existing_customer']
                    if isinstance(customer_obj, Customer):  # Check if it's a Customer object
                        cleaned_data['existing_customer'] = customer_obj.id  # Store just the ID
                
                # Store the modified data in session
                form_data['step1'] = cleaned_data
                request.session['booking_request_form_data'] = form_data
                
                # Proceed to step 2
                return redirect('public_booking_request_create', step=2)
            else:
                return render(request, 'booking/public_booking_request_step1.html', {'form': form})
        
        elif step == 2:
            # Process step 2: Service selection
            form = ServiceSelectionForm(request.POST)
            
            if form.is_valid():
                # Create a copy of cleaned_data to modify
                cleaned_data = form.cleaned_data.copy()
                
                # Replace the Service object with just its ID
                if 'service' in cleaned_data and cleaned_data['service'] is not None:
                    service_obj = cleaned_data['service']
                    cleaned_data['service'] = service_obj.id  # Store just the ID
                
                # Convert date and time objects to string format
                if 'date' in cleaned_data and cleaned_data['date'] is not None:
                    cleaned_data['date'] = cleaned_data['date'].isoformat()  # Convert to ISO format string
                    
                if 'time' in cleaned_data and cleaned_data['time'] is not None:
                    cleaned_data['time'] = cleaned_data['time'].isoformat()  # Convert to ISO format string
                    
                # Handle the datetime object if it exists
                if 'date_time' in cleaned_data and cleaned_data['date_time'] is not None:
                    cleaned_data['date_time'] = cleaned_data['date_time'].isoformat()  # Convert to ISO format string
                
                # Store the modified data in session
                form_data['step2'] = cleaned_data
                request.session['booking_request_form_data'] = form_data
                
                # Proceed to step 3
                return redirect('public_booking_request_create', step=3)
            else:
                return render(request, 'booking/public_booking_request_step2.html', {'form': form})    
        elif step == 3:
            # Process step 3: Additional services
            # Get the main service selected in step 2
            service_id = form_data.get('step2', {}).get('service')
            if service_id:
                main_service = get_object_or_404(Service, pk=service_id)
                form = AdditionalServicesForm(request.POST, main_service=main_service)
                
                if form.is_valid():
                    # Store form data in session
                    form_data['step3'] = {
                        'selected_services': form.get_selected_services(),
                        'notes': form.cleaned_data.get('notes', '')
                    }
                    request.session['booking_request_form_data'] = form_data
                    
                    # Proceed to step 4
                    return redirect('public_booking_request_create', step=4)
                else:
                    return render(request, 'booking/public_booking_request_step3.html', {
                        'form': form,
                        'main_service': main_service
                    })
            else:
                messages.error(request, "Please select a service first.")
                return redirect('public_booking_request_create', step=2)
        
        elif step == 4:
            # Process step 4: Submit booking request
            # Get data from previous steps
            step1_data = form_data.get('step1', {})
            step2_data = form_data.get('step2', {})
            step3_data = form_data.get('step3', {})

            
            
            # Create booking request
            with transaction.atomic():
                booking_request = BookingRequest()
                
                # Set customer information
                customer_choice = step1_data.get('customer_choice')
                # Creating a booking request in step 4
                if customer_choice == 'existing':
                    customer_id = step1_data.get('existing_customer_id')
                    if customer_id:
                        booking_request.existing_customer_id = customer_id
                        booking_request.is_new_customer = False
                else:
                    booking_request.is_new_customer = True
                    booking_request.first_name = step1_data.get('first_name')
                    booking_request.last_name = step1_data.get('last_name')
                    booking_request.phone = step1_data.get('phone')
                    booking_request.email = step1_data.get('email')  # Add email
                    booking_request.address = step1_data.get('address')
                
                # Set service and time information
                booking_request.service_id = step2_data.get('service')
                booking_request.date_time = step2_data.get('date_time')
                
                # Set additional services
                booking_request.additional_services = step3_data.get('selected_services', [])
                
                # Set notes
                booking_request.notes = step3_data.get('notes', '')
                
                # Save booking request
                booking_request.save()
            
            # Clear session data
            if 'booking_request_form_data' in request.session:
                del request.session['booking_request_form_data']
            
            # Show success message
            messages.success(request, "Your booking request has been submitted successfully. We will contact you shortly to confirm your appointment.")
            
            # Redirect to confirmation page
            return redirect('public_booking_request_confirmation', request_id=booking_request.request_id)
            
        else:
            # Invalid step, redirect to step 1
            return redirect('public_booking_request_create', step=1)


class PublicBookingRequestConfirmationView(View):
    """Confirmation page after submitting a booking request"""
    
    def get(self, request, *args, **kwargs):
        request_id = kwargs.get('request_id')
        booking_request = get_object_or_404(BookingRequest, request_id=request_id)
        
        return render(request, 'booking/public_booking_request_confirmation.html', {
            'booking_request': booking_request
        })


class StaffBookingRequestListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """List view for staff to see booking requests"""
    model = BookingRequest
    template_name = 'booking/staff_booking_request_list.html'
    context_object_name = 'booking_requests'
    
    def get_queryset(self):
        # Show pending requests first, then by date
        return BookingRequest.objects.filter(status='PENDING').order_by('date_time')


class StaffBookingRequestDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    """Detail view for staff to see booking request details"""
    model = BookingRequest
    template_name = 'booking/staff_booking_request_detail.html'
    context_object_name = 'booking_request'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking_request = self.object
        
        # Get the main service
        main_service = None
        if booking_request.service_id:
            try:
                main_service = Service.objects.get(pk=booking_request.service_id)
            except Service.DoesNotExist:
                pass
        
        # Get additional services
        additional_services = []
        if booking_request.additional_services:
            try:
                # Assuming additional_services is stored as a list of service IDs
                service_ids = booking_request.additional_services
                if isinstance(service_ids, list):
                    additional_services = Service.objects.filter(pk__in=service_ids)
            except Exception as e:
                pass
        
        # Calculate totals
        total_duration = main_service.duration if main_service else 0
        total_price = main_service.price if main_service else 0
        
        for service in additional_services:
            total_duration += service.duration
            total_price += service.price
        
        # Add to context
        context['main_service'] = main_service
        context['additional_services'] = additional_services
        context['total_duration'] = total_duration
        context['total_price'] = total_price
        
        return context

    



@method_decorator(require_POST, name='dispatch')
class StaffBookingRequestApproveView(LoginRequiredMixin, StaffRequiredMixin, View):
    """View for staff to approve booking requests"""
    
    def post(self, request, *args, **kwargs):
        booking_request = get_object_or_404(BookingRequest, pk=kwargs.get('pk'))
        
        # Only allow approving pending requests
        if booking_request.status != 'PENDING':
            messages.error(request, "This booking request has already been processed.")
            return redirect('staff_booking_request_detail', pk=booking_request.pk)
        
        with transaction.atomic():
            # Create/get customer
            if booking_request.is_new_customer:
                # Create new customer
                customer = Customer.objects.create(
                    first_name=booking_request.first_name,
                    last_name=booking_request.last_name,
                    phone=booking_request.phone,
                    address=booking_request.address,
                    created_by=request.user
                )
            else:
                # Use existing customer
                customer = booking_request.existing_customer
            
            # Create booking
            booking = Booking.objects.create(
                customer=customer,
                service=booking_request.service,
                date_time=booking_request.date_time,
                status='CONFIRMED',
                notes=booking_request.notes,
                created_by=request.user,
                updated_by=request.user
            )
            
            # Add additional services if any
            if booking_request.additional_services:
                # Handle additional services here
                # This would depend on your implementation of additional services
                pass
            
            # Update booking request status
            booking_request.status = 'APPROVED'
            booking_request.reviewed_by = request.user
            booking_request.save()
        
        messages.success(request, "Booking request approved and converted to a booking successfully.")
        return redirect('booking_detail', pk=booking.pk)


@method_decorator(require_POST, name='dispatch')
class StaffBookingRequestRejectView(LoginRequiredMixin, StaffRequiredMixin, View):
    """View for staff to reject booking requests"""
    
    def post(self, request, *args, **kwargs):
        booking_request = get_object_or_404(BookingRequest, pk=kwargs.get('pk'))
        
        # Only allow rejecting pending requests
        if booking_request.status != 'PENDING':
            messages.error(request, "This booking request has already been processed.")
            return redirect('staff_booking_request_detail', pk=booking_request.pk)
        
        # Update booking request status
        booking_request.status = 'REJECTED'
        booking_request.reviewed_by = request.user
        booking_request.save()
        
        messages.success(request, "Booking request rejected successfully.")
        return redirect('staff_booking_request_list')