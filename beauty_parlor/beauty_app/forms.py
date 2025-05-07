from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from .models import CustomUser, Customer, Service, Discount, Booking, Sale
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
        fields = ('first_name', 'last_name', 'phone_number', 'user_type', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict user_type to staff or admin only
        self.fields['user_type'].choices = [
            choice for choice in CustomUser.USER_TYPE_CHOICES 
            if choice[0] in ['STAFF', 'ADMIN']
        ]

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
        fields = ('first_name', 'last_name', 'phone', 'address', 'notes')
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

class DiscountForm(forms.ModelForm):
    """Form for creating and updating time-based service discounts."""
    
    class Meta:
        model = Discount
        fields = ('service', 'percentage', 'start_date', 'end_date')
        widgets = {
            'start_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'end_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
        }
        help_texts = {
            'start_date': "Enter the current time or a future datetime when this discount should start.",
            'end_date': "Enter a future datetime after the start time when this discount should end."
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
    def clean(self):
        cleaned_data = super().clean()
        service = cleaned_data.get('service')
        start_datetime = cleaned_data.get('start_date')
        end_datetime = cleaned_data.get('end_date')
        
        # Get current datetime with a small buffer to account for form submission time
        current_datetime = timezone.now() - timezone.timedelta(seconds=30)
        
        # Validate full datetime (including time component)
        if start_datetime and end_datetime:
            # Ensure end datetime is always after start datetime
            if start_datetime >= end_datetime:
                raise ValidationError("End datetime must be after start datetime.")
            
            # Always ensure start datetime is not in the past for both new and updated discounts
            if start_datetime < current_datetime:
                raise ValidationError("Start datetime cannot be in the past. Please use the current time or a future datetime.")
        
        # Check for conflicting discounts, but exclude the current discount when updating
        if service:
            now = timezone.now()
            query = Q(start_date__lte=now, end_date__gt=now) | Q(start_date__gt=now)
            
            # If updating an existing discount, exclude the current instance from the check
            if self.instance.pk:
                existing_discount = Discount.objects.filter(
                    service=service
                ).filter(query).exclude(pk=self.instance.pk).exists()
            else:
                existing_discount = Discount.objects.filter(
                    service=service
                ).filter(query).exists()
            
            if existing_discount:
                raise ValidationError("This service already has an active or upcoming discount.")
        
        return cleaned_data


# Booking Forms
# ============================

class BookingForm(forms.ModelForm):
    """Form for creating and updating bookings."""
    
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
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Filter active services only
        services = Service.objects.filter(active=True)
        choices = [(s.id, s.name) for s in services]
        self.fields['service'].choices = choices
        
        # Add data-price attribute to each service option
        for service in services:
            self.fields['service'].widget.attrs.update({
                f'data-price-{service.id}': service.price
            })
            
    def clean(self):
        cleaned_data = super().clean()
        date_time = cleaned_data.get('date_time')
        
        # # Validate booking time
        # if date_time and date_time < timezone.now() and not self.instance.pk:
            # raise ValidationError("Booking time cannot be in the past.")
            
        return cleaned_data

class AdminBookingForm(BookingForm):
    """Extended booking form with discount options for admins."""
    
    class Meta(BookingForm.Meta):
        model = Booking
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


