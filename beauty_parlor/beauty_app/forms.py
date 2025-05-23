from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from .models import CustomUser, Customer, Service, Discount, Booking, Sale, AdditionalService
from .utils import generate_username

# ============================
# CustomUser Forms
# ============================

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users with custom username generation."""
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'user_type', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make sure required fields are marked as such
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        # self.fields['email'].required = True
        self.fields['phone_number'].required = True
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Generate username if not provided (first letter of first name + last name)
        if not user.username and user.first_name and user.last_name:
            user.username = generate_username(user.first_name, user.last_name)
            
        if commit:
            user.save()
        return user

class StaffCreationForm(CustomUserCreationForm):
    """Form specifically for admin to create staff users."""
    
    class Meta(CustomUserCreationForm.Meta):
        model = CustomUser
        fields = ('first_name', 'last_name', 'phone_number', 'user_type', 'primary_service', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict user_type to staff or admin only
        self.fields['user_type'].choices = [
            choice for choice in CustomUser.USER_TYPE_CHOICES 
            if choice[0] in ['STAFF', 'ADMIN', 'STAFFLEVEL2']
        ]
        
        # Show primary_service field only for STAFFLEVEL2
        # Add any needed attributes or styling
        self.fields['primary_service'].queryset = Service.objects.filter(active=True)
        self.fields['primary_service'].required = False
        
        # Add conditional visibility via JavaScript classes
        self.fields['primary_service'].widget.attrs.update({
            'class': 'form-control service-field',
            'data-requires-usertype': 'STAFFLEVEL2'
        })

class CustomUserUpdateForm(forms.ModelForm):
    """Form for updating existing users."""
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name','phone_number', 'user_type', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make sure required fields are marked as such
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        # self.fields['email'].required = True
        self.fields['phone_number'].required = True
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class ProfileUpdateForm(forms.ModelForm):
    """Form for users to update their own profile."""
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

# ============================
# Customer Forms
# ============================

class CustomerForm(forms.ModelForm):
    """Form for creating and updating customers."""
    
    class Meta:
        model = Customer
        fields = ('first_name', 'last_name', 'phone','email', 'address', 'notes')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CustomerSearchForm(forms.Form):
    """Form for searching customers."""
    
    query = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email or phone'
        })
    )

# ============================
# Service Forms
# ============================


class ServiceForm(forms.ModelForm):
    """Form for creating and updating services."""
    
    class Meta:
        model = Service
        fields = ('name', 'description', 'price', 'duration', 'active', 'image')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            if field != 'image':  # Don't add form-control to image field
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Custom field for duration with help text
        self.fields['duration'].help_text = "Duration in minutes"
        
        # Help text for image field
        self.fields['image'].help_text = "Upload an image for this service (recommended size: 800x600px)"
        self.fields['image'].widget.attrs.update({'class': 'form-control-file'})

# ============================
# Discount Forms
# ============================
# beauty_app/forms.py - Updated DiscountForm

class DiscountForm(forms.Form):
    """Form for creating and updating time-based service discounts with multi-select."""
    
    DISCOUNT_TYPE_CHOICES = (
        ('single', 'Single Service'),
        ('multiple', 'Selected Services'),
        ('all', 'All Active Services'),
    )
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter discount name (e.g., Christmas Bonus, Flash Sale)'}),
        help_text="Give this discount campaign a memorable name"
    )
    
    discount_type = forms.ChoiceField(
        choices=DISCOUNT_TYPE_CHOICES,
        initial='single',
        widget=forms.RadioSelect,
        help_text="Choose whether to apply discount to one, multiple, or all services"
    )
    
    single_service = forms.ModelChoiceField(
        queryset=Service.objects.filter(active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select a service for the discount"
    )
    
    multiple_services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select multiple services for the discount"
    )
    
    percentage = forms.DecimalField(
        max_digits=5, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
        help_text="Discount percentage (0-100%)"
    )
    
    start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        help_text="Enter the current time or a future datetime when this discount should start."
    )
    
    end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        help_text="Enter a future datetime after the start time when this discount should end."
    )
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        
        # If editing an existing discount
        if self.instance:
            self.fields['name'].initial = self.instance.name
            self.fields['discount_type'].initial = 'single'
            self.fields['single_service'].initial = self.instance.service
            self.fields['percentage'].initial = self.instance.percentage
            self.fields['start_date'].initial = self.instance.start_date
            self.fields['end_date'].initial = self.instance.end_date
            
            # Disable discount type selection when editing
            self.fields['discount_type'].widget.attrs['disabled'] = True
            self.fields['discount_type'].help_text = "Discount type cannot be changed when editing"
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 3:
                raise ValidationError("Discount name must be at least 3 characters long.")
        return name
    
    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        single_service = cleaned_data.get('single_service')
        multiple_services = cleaned_data.get('multiple_services')
        start_datetime = cleaned_data.get('start_date')
        end_datetime = cleaned_data.get('end_date')
        name = cleaned_data.get('name')
        
        # Get current datetime with a small buffer
        current_datetime = timezone.now() - timezone.timedelta(seconds=30)
        
        # Validate service selection based on discount type
        if discount_type == 'single' and not single_service:
            raise ValidationError("Please select a service for single service discount.")
        elif discount_type == 'multiple' and not multiple_services:
            raise ValidationError("Please select at least one service for multiple services discount.")
        
        # Validate datetime fields
        if start_datetime and end_datetime:
            if start_datetime >= end_datetime:
                raise ValidationError("End datetime must be after start datetime.")
            
            if start_datetime < current_datetime:
                raise ValidationError("Start datetime cannot be in the past. Please use the current time or a future datetime.")
        
        # Get services to check based on discount type
        services_to_check = []
        if discount_type == 'single' and single_service:
            services_to_check = [single_service]
        elif discount_type == 'multiple':
            services_to_check = multiple_services
        elif discount_type == 'all':
            services_to_check = Service.objects.filter(active=True)
        
        # Check for conflicting discounts for all services
        services_with_conflicts = []
        for service in services_to_check:
            now = timezone.now()
            query = Q(start_date__lte=now, end_date__gt=now) | Q(start_date__gt=now)
            
            # Exclude current instance when updating
            if self.instance and self.instance.pk and self.instance.service == service:
                existing_discount = Discount.objects.filter(
                    service=service
                ).filter(query).exclude(pk=self.instance.pk).exists()
            else:
                existing_discount = Discount.objects.filter(
                    service=service
                ).filter(query).exists()
            
            if existing_discount:
                services_with_conflicts.append(service.name)
        
        if services_with_conflicts:
            if len(services_with_conflicts) == 1:
                raise ValidationError(f"The service '{services_with_conflicts[0]}' already has an active or upcoming discount.")
            else:
                raise ValidationError(f"The following services already have active or upcoming discounts: {', '.join(services_with_conflicts)}")
        
        return cleaned_data
    
    def get_selected_services(self):
        """Helper method to get the list of services based on discount type selection"""
        if not self.is_valid():
            return []
            
        discount_type = self.cleaned_data.get('discount_type')
        
        if discount_type == 'single':
            return [self.cleaned_data.get('single_service')]
        elif discount_type == 'multiple':
            return list(self.cleaned_data.get('multiple_services', []))
        elif discount_type == 'all':
            return list(Service.objects.filter(active=True))
        
        return []


# Booking Forms
# ============================
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('customer', 'service', 'date_time', 'status', 'notes')
        widgets = {
            'date_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        services = Service.objects.filter(active=True)
        choices = [(s.id, f"{s.name} - {s.duration} min") for s in services]
        self.fields['service'].choices = choices
        
        for service in services:
            self.fields['service'].widget.attrs.update({
                f'data-price-{service.id}': service.price,
                f'data-duration-{service.id}': service.duration
            })
        
        self.current_booking = None
        if self.instance and self.instance.pk:
            self.current_booking = self.instance
            
    def clean(self):
        cleaned_data = super().clean()
        date_time = cleaned_data.get('date_time')
        
        if date_time and date_time < timezone.now() and not self.instance.pk:
            raise ValidationError("Booking time cannot be in the past.")
            
        return cleaned_data
    
    def get_available_services_with_discounts(self):
        now = timezone.now()
        
        # Determine main service ID
        main_service_id = None
        if self.data.get('service'):  # Check form submission first
            main_service_id = self.data.get('service')
        elif self.instance.pk and self.instance.service:  # Then existing booking
            main_service_id = self.instance.service.id
        elif 'service' in self.initial:  # Finally, initial data
            main_service_id = self.initial['service'].id if hasattr(self.initial['service'], 'id') else self.initial['service']
        
        # Get active services, excluding the main service if specified
        services = Service.objects.filter(active=True)
        if main_service_id:
            try:
                # Ensure main_service_id is a valid integer
                main_service_id = int(main_service_id)
                services = services.exclude(id=main_service_id)
            except (ValueError, TypeError):
                pass  # If main_service_id is invalid, proceed without exclusion
        
        # Get booking date for discount checks
        booking_date = now
        if self.data.get('date_time'):
            booking_date = self.data.get('date_time')
        elif self.instance.pk and self.instance.date_time:
            booking_date = self.instance.date_time
        elif 'date_time' in self.initial:
            booking_date = self.initial['date_time']
        
        result = []
        for service in services:
            active_discount = Discount.objects.filter(
                service=service,
                start_date__lte=booking_date,
                end_date__gte=booking_date
            ).order_by('-percentage').first()
            
            regular_price = float(service.price)
            discounted_price = regular_price
            discount_percentage = 0
            discount_amount = 0
            
            if active_discount:
                discount_percentage = float(active_discount.percentage)
                discount_amount = regular_price * (discount_percentage / 100)
                discounted_price = regular_price - discount_amount
            
            service_data = {
                'service': service,
                'price': regular_price,
                'duration': service.duration,
                'has_discount': bool(active_discount),
                'discount': active_discount,
                'discount_percentage': discount_percentage,
                'discount_amount': discount_amount,
                'discounted_price': discounted_price
            }
            
            result.append(service_data)
        
        return result


class AdminBookingForm(BookingForm):
    class Meta(BookingForm.Meta):
        fields = ('customer', 'service', 'date_time', 'status', 'custom_discount', 'notes')
        
    def clean_custom_discount(self):
        custom_discount = self.cleaned_data.get('custom_discount')
        if custom_discount and (custom_discount < 0 or custom_discount > 100):
            raise ValidationError("Discount must be between 0 and 100%.")
        return custom_discount

class BookingSearchForm(forms.Form):
    """Form for searching and filtering bookings."""
    
    query = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer or Service'
        })
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + list(Booking.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
class SaleForm(forms.ModelForm):
    """Form for creating sales records with enhanced discount display."""
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('MOBILE_PAYMENT', 'Mobile Payment'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]
    
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES)
    
    class Meta:
        model = Sale
        fields = ('booking', 'payment_amount', 'payment_method', 'payment_discount')
        widgets = {
            'payment_amount': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'readonly': 'readonly'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Add help text to payment_discount field
        self.fields['payment_discount'].help_text = "Special discount to apply at payment time (0-100%)"
        self.fields['payment_discount'].widget.attrs.update({
            'min': '0', 
            'max': '100',
            'step': '0.01'
        })
        
        # Initialize payment_discount to 0
        self.initial['payment_discount'] = 0
        
        # Store the current booking for later use
        self.current_booking = None
        
        # If a booking is already assigned, make the field readonly
        if self.instance and self.instance.pk:
            self.fields['booking'].disabled = True
            self.current_booking = self.instance.booking
        else:
            # Only show completed bookings that don't already have a sale
            bookings = Booking.objects.filter(
                status='COMPLETED'
            ).exclude(
                sale__isnull=False
            )
            self.fields['booking'].queryset = bookings
            
            # Check if there's an initial booking value
            if 'initial' in kwargs and 'booking' in kwargs['initial']:
                self.current_booking = kwargs['initial']['booking']
            
            # Add data attributes for each booking option
            for booking in bookings:
                # Get detailed discount information
                service_discount_info = self.get_service_discount_info(booking)
                custom_discount_info = self.get_custom_discount_info(booking)
                
                # Format the data attributes as string to match how they'll be accessed in JS
                self.fields['booking'].widget.attrs.update({
                    f'data-service-name-{booking.pk}': booking.service.name,
                    f'data-regular-price-{booking.pk}': float(booking.service.price),
                    f'data-final-price-{booking.pk}': float(booking.get_final_price()),
                    f'data-service-id-{booking.pk}': booking.service.id,
                    
                    # Add detailed discount information
                    f'data-has-service-discount-{booking.pk}': 'true' if service_discount_info else 'false',
                    f'data-has-custom-discount-{booking.pk}': 'true' if custom_discount_info else 'false',
                })
                
                # Add service discount details if available
                if service_discount_info:
                    self.fields['booking'].widget.attrs.update({
                        f'data-service-discount-percentage-{booking.pk}': service_discount_info['percentage'],
                        f'data-service-discount-amount-{booking.pk}': service_discount_info['amount'],
                        f'data-price-after-service-discount-{booking.pk}': service_discount_info['price_after'],
                    })
                
                # Add custom discount details if available
                if custom_discount_info:
                    self.fields['booking'].widget.attrs.update({
                        f'data-custom-discount-percentage-{booking.pk}': custom_discount_info['percentage'],
                        f'data-custom-discount-amount-{booking.pk}': custom_discount_info['amount'],
                        f'data-price-after-custom-discount-{booking.pk}': custom_discount_info['price_after'],
                    })
    
    def get_service_discount_info(self, booking):
        """Get detailed service discount information for a booking."""
        if not booking.service_discount:
            return None
            
        regular_price = float(booking.service.price)
        percentage = float(booking.service_discount.percentage)
        amount = regular_price * (percentage / 100)
        price_after = regular_price - amount
        
        return {
            'percentage': percentage,
            'amount': amount,
            'price_after': price_after
        }
    
    def get_custom_discount_info(self, booking):
        """Get detailed custom discount information for a booking."""
        if booking.custom_discount <= 0:
            return None
            
        # Start with regular price or price after service discount
        base_price = float(booking.service.price)
        if booking.service_discount:
            service_discount_percentage = float(booking.service_discount.percentage)
            base_price = base_price * (1 - service_discount_percentage / 100)
        
        percentage = float(booking.custom_discount)
        amount = base_price * (percentage / 100)
        price_after = base_price - amount
        
        return {
            'percentage': percentage,
            'amount': amount,
            'price_after': price_after
        }
    
    def get_other_services_with_discounts(self):
        """Get other active services excluding the one in the current booking, with discount info."""
        if not self.current_booking:
            return []
        
        from django.utils import timezone
        now = timezone.now()
        
        # Get all active services except current
        services = Service.objects.filter(active=True).exclude(id=self.current_booking.service.id)
        
        # Prepare result list with discount info
        result = []
        for service in services:
            # Check for active discounts
            active_discount = Discount.objects.filter(
                service=service,
                start_date__lte=now,
                end_date__gte=now
            ).order_by('-percentage').first()  # Get highest discount if multiple exist
            
            # Calculate discounted price if applicable
            regular_price = float(service.price)
            discounted_price = regular_price
            discount_amount = 0
            
            if active_discount:
                discount_percentage = float(active_discount.percentage)
                discount_amount = regular_price * (discount_percentage / 100)
                discounted_price = regular_price - discount_amount
            
            service_data = {
                'service': service,
                'regular_price': regular_price,
                'discount': active_discount,
                'discount_amount': discount_amount,
                'discounted_price': discounted_price
            }
            
            result.append(service_data)
        
        return result
    
    def clean(self):
        cleaned_data = super().clean()
        booking = cleaned_data.get('booking')
        payment_amount = cleaned_data.get('payment_amount')
        payment_discount = cleaned_data.get('payment_discount') or 0
        
        # Validate payment discount
        if payment_discount and (payment_discount < 0 or payment_discount > 100):
            self.add_error('payment_discount', "Discount must be between 0 and 100%.")
        
        # Validate payment amount only if we have a booking and payment amount
        if booking and payment_amount is not None:
            # Get the base price (after all booking discounts)
            booking_price = booking.get_final_price()
            
            # Apply payment discount if provided
            if payment_discount > 0:
                expected_amount = booking_price * (1 - payment_discount / 100)
            else:
                expected_amount = booking_price
                
            # Check if payment amount is less than expected (allow a small tolerance for floating point precision)
            if float(payment_amount) < float(expected_amount) * 0.99:  # Allow 1% tolerance
                self.add_error(
                    'payment_amount', 
                    f"Payment amount (GHS{payment_amount}) is less than the expected amount (GHS{expected_amount:.2f})."
                )
                
        return cleaned_data
    


class SalesReportForm(forms.Form):
    """Form for generating sales reports."""
    
    start_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    service = forms.ModelChoiceField(
        required=False,
        queryset=Service.objects.filter(active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Services"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("End date must be after start date.")
            
        return cleaned_data
    
class SaleSearchForm(forms.Form):
    """Form for searching and filtering sales."""
    
    query = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Receipt #, Customer or Service'
        })
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    payment_method = forms.ChoiceField(
        required=False,
        choices=[('', 'All Methods')] + list(SaleForm.PAYMENT_METHOD_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    min_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min Amount'
        })
    )
    
    max_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max Amount'
        })
    )

# ============================


class TherapistAssignmentForm(forms.Form):
    """Form for assigning therapists to services in a booking"""
    service = forms.ModelChoiceField(
        queryset=Service.objects.none(),
        label="Service",
        widget=forms.Select(attrs={'class': 'form-control service-select'})
    )
    
    therapist = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        label="Assign Therapist",
        widget=forms.Select(attrs={'class': 'form-control therapist-select'})
    )
    
    is_primary = forms.BooleanField(
        required=False, 
        initial=True,
        label="Primary Therapist",
        help_text="Check if this therapist is responsible for this service"
    )
    
    def __init__(self, *args, **kwargs):
        booking = kwargs.pop('booking', None)
        super().__init__(*args, **kwargs)
        
        if booking:
            # Collect all services (main + additional)
            service_ids = [booking.service.id]
            additional_services = AdditionalService.objects.filter(booking=booking)
            for add_service in additional_services:
                service_ids.append(add_service.id)
                
            # Set available services
            self.fields['service'].queryset = Service.objects.filter(id__in=service_ids)
            
            # Default to main service
            self.fields['service'].initial = booking.service
            
            # Set the initial therapist queryset
            self.fields['therapist'].queryset = CustomUser.objects.filter(
                user_type__in=[ 'STAFFLEVEL2'],
                is_active=True
            )


class StaffUpdateForm(forms.ModelForm):
    """Form specifically for updating staff users, including primary_service field."""
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'phone_number', 'user_type', 'primary_service', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make sure required fields are marked as such
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['phone_number'].required = True
        
        # Restrict user_type to staff levels only
        self.fields['user_type'].choices = [
            choice for choice in CustomUser.USER_TYPE_CHOICES 
            if choice[0] in ['STAFF', 'ADMIN', 'STAFFLEVEL2']
        ]
        
        # Set up primary_service field
        self.fields['primary_service'].queryset = Service.objects.filter(active=True)
        self.fields['primary_service'].required = False
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Add conditional visibility for primary_service field
        self.fields['primary_service'].widget.attrs.update({
            'class': 'form-control service-field',
            'data-requires-usertype': 'STAFFLEVEL2'
        })