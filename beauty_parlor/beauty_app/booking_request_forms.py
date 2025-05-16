from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import BookingTherapistAssignment, Customer, Service, BookingRequest, CustomUser

# class CustomerSelectionForm(forms.Form):
#     customer_choice = forms.ChoiceField(
#         choices=(
#             ('existing', 'I am an existing customer'),
#             ('new', 'I am a new customer')
#         ),
#         widget=forms.RadioSelect,
#         initial='new'
#     )
    
#     existing_customer = forms.ModelChoiceField(
#         queryset=Customer.objects.all().order_by('first_name', 'last_name'),
#         required=False,
#         empty_label="Select your name",
#         widget=forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'})
#     )
    
#     # Fields for new customer
#     first_name = forms.CharField(max_length=100, required=False)
#     last_name = forms.CharField(max_length=100, required=False)
#     phone = forms.CharField(max_length=15, required=False)
#     address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    
#     def clean(self):
#         cleaned_data = super().clean()
#         customer_choice = cleaned_data.get('customer_choice')
        
#         if customer_choice == 'existing':
#             if not cleaned_data.get('existing_customer'):
#                 raise ValidationError("Please select your name from the list.")
#         elif customer_choice == 'new':
#             # Validate new customer fields
#             if not cleaned_data.get('first_name'):
#                 raise ValidationError("First name is required for new customers.")
#             if not cleaned_data.get('last_name'):
#                 raise ValidationError("Last name is required for new customers.")
#             if not cleaned_data.get('phone'):
#                 raise ValidationError("Phone number is required for new customers.")
                
#         return cleaned_data


# forms.py
class CustomerSelectionForm(forms.Form):
    customer_choice = forms.ChoiceField(
        choices=[('existing', 'I am an existing customer'), ('new', 'I am a new customer')],
        widget=forms.RadioSelect(),
        initial='new'
    )
    
    # Email lookup field for existing customers
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )
    
    # Fields for new customer
    first_name = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email_new = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        customer_choice = cleaned_data.get('customer_choice')
        
        if customer_choice == 'existing':
            email = cleaned_data.get('email')
            if not email:
                raise ValidationError("Please provide your email address.")
            
            # Check if customer with this email exists
            try:
                customer = Customer.objects.get(email=email)
                # Store the customer ID for later use
                cleaned_data['existing_customer_id'] = customer.id
                # Add customer data for display purposes
                cleaned_data['customer_data'] = {
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'phone': customer.phone,
                    'email': customer.email,
                    'address': customer.address
                }
            except Customer.DoesNotExist:
                raise ValidationError("No customer found with this email. Please try again or register as a new customer.")
                
        elif customer_choice == 'new':
            # Validate new customer fields
            first_name = cleaned_data.get('first_name')
            last_name = cleaned_data.get('last_name')
            phone = cleaned_data.get('phone')
            email_new = cleaned_data.get('email_new')
            
            if not first_name:
                raise ValidationError("First name is required for new customers.")
            if not last_name:
                raise ValidationError("Last name is required for new customers.")
            if not phone:
                raise ValidationError("Phone number is required for new customers.")
            if not email_new:
                raise ValidationError("Email is required for new customers.")
            
            # Check if email is already in use
            if Customer.objects.filter(email=email_new).exists():
                raise ValidationError("This email is already registered. Please log in as an existing customer.")
                
        return cleaned_data


class ServiceSelectionForm(forms.Form):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(active=True),
        label="Select Service",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    date = forms.DateField(
        label="Select Date",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    time = forms.TimeField(
        label="Select Time",
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        required=True
    )
    preferred_therapist = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(user_type='COMMONSTAFF', is_active=True),
        label="Preferred Therapist (Optional)",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    # Add this method to dynamically update available therapists
    def update_therapists(self, service_id, date_time=None):
        """Dynamically update the therapist field based on the selected service and time"""
        if not service_id:
            self.fields['preferred_therapist'].queryset = CustomUser.objects.filter(
                user_type='COMMONSTAFF', is_active=True
            )
            return
            
        # Filter therapists who can provide this service
        therapists = CustomUser.objects.filter(
            user_type='COMMONSTAFF', 
            is_active=True
        )
        
        # If we have date_time, we can filter available therapists
        if date_time:
            # Get therapists who don't have conflicting bookings
            busy_therapists = BookingTherapistAssignment.objects.filter(
                booking__date_time=date_time,
                booking__status__in=['PENDING', 'CONFIRMED']
            ).values_list('therapist_id', flat=True)
            
            # Exclude busy therapists
            therapists = therapists.exclude(id__in=busy_therapists)
            
        self.fields['preferred_therapist'].queryset = therapists
# class ServiceSelectionForm(forms.Form):
#     service = forms.ModelChoiceField(
#         queryset=Service.objects.filter(active=True),
#         empty_label="Select a service",
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )
    
#     date = forms.DateField(
#         widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
#         initial=timezone.now().date
#     )
    
#     time = forms.TimeField(
#         widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
#         initial=timezone.now().time
#     )
#      # Add therapist field
#     therapist = forms.ModelChoiceField(
#         queryset=CustomUser.objects.none(),  # Will be populated via JS
#         required=False,
#         empty_label="Select a therapist (optional)",
#         widget=forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'})
#     )
    
#     def clean(self):
#         cleaned_data = super().clean()
#         date = cleaned_data.get('date')
#         time = cleaned_data.get('time')
        
#         if date and time:
#             # Combine date and time into a datetime object
#             from datetime import datetime
#             date_time = datetime.combine(date, time)
            
#             # Convert to timezone-aware datetime
#             from django.utils import timezone
#             date_time = timezone.make_aware(date_time)
            
#             # Check if the date_time is in the past
#             if date_time < timezone.now():
#                 raise ValidationError("Booking time cannot be in the past.")
            
#             cleaned_data['date_time'] = date_time
            
#         return cleaned_data

class AdditionalServicesForm(forms.Form):
    """Form for selecting additional services"""
    
    def __init__(self, *args, **kwargs):
        # Get available services excluding the main service
        main_service = kwargs.pop('main_service', None)
        super().__init__(*args, **kwargs)
        
        if main_service:
            services = Service.objects.filter(active=True).exclude(pk=main_service.pk)
            
            for service in services:
                self.fields[f'service_{service.pk}'] = forms.BooleanField(
                    label=f"{service.name} (GHS{service.price} - {service.duration} min)",
                    required=False
                )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any special requests or notes?'}),
        required=False
    )
    
    def get_selected_services(self):
        """Returns a list of selected service IDs"""
        selected_services = []
        
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('service_') and value:
                service_id = field_name.split('_')[1]
                selected_services.append(int(service_id))
                
        return selected_services

class BookingRequestForm(forms.ModelForm):
    """Form for creating a booking request (combines all the previous forms)"""
    
    class Meta:
        model = BookingRequest
        fields = ['is_new_customer', 'existing_customer', 'first_name', 'last_name', 
                 'phone', 'address', 'service', 'date_time', 'additional_services', 'notes']