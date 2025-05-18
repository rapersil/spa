# beauty_app/models.py

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from .validators import phone_validator, price_validator, discount_validator, email_validator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from .utils import generate_username
from .mixins import AuditableMixin

# beauty_app/models.py
class CustomUser(AuditableMixin, AbstractUser):
    USER_TYPE_CHOICES = (
        ('STAFF', 'Staff'),
        ('ADMIN', 'Admin'),
        ('SUPERADMIN', 'Super Admin'),
        ('STAFFLEVEL2', 'Common Staff'),
    )
    user_id = models.CharField(max_length=15, unique=True, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, validators=[phone_validator])
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    password_change_required = models.BooleanField(default=False, 
                                                  help_text="User must change password at next login")
    # New field for service assignment
    primary_service = models.ForeignKey(
        'Service', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='primary_staff',
        help_text="The primary service this staff member provides"
    )
    
    def save(self, *args, **kwargs):
        # Generate user_id if it doesn't exist
        if not self.user_id:
            # Create a unique ID based on UUID
            self.user_id = f"USR{str(uuid.uuid4())[:4]}".upper()
        
        # Generate username if it's a new user
        if not self.pk and not self.username and self.first_name and self.last_name:
            self.username = generate_username(self.first_name, self.last_name)
            
        super().save(*args, **kwargs)

class Customer(AuditableMixin, models.Model):
    customer_id = models.CharField(max_length=15, unique=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(validators=[email_validator])
    phone = models.CharField(max_length=15, validators=[phone_validator])
    address = models.TextField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            # Create a unique ID based on UUID
            self.customer_id = f"CST{str(uuid.uuid4())[:8]}".upper()
            
            # Ensure the ID is unique (extremely unlikely to be needed, but added for safety)
            while Customer.objects.filter(customer_id=self.customer_id).exists():
                self.customer_id = f"CST{str(uuid.uuid4())[:8]}".upper()
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.customer_id})"

# beauty_app/models.py (Service model update)

class Service(AuditableMixin, models.Model):
    service_id = models.CharField(max_length=15, unique=True, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[price_validator])
    duration = models.IntegerField(help_text="Duration in minutes")
    active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='service_images/', null=True, blank=True, 
                              help_text="Upload an image for this service")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(CustomUser, related_name='updated_services',
                                   on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.service_id:
            # Create a unique ID based on UUID
            self.service_id = f"SRV{str(uuid.uuid4())[:8]}".upper()
            
            # Ensure the ID is unique (extremely unlikely to be needed, but added for safety)
            while Service.objects.filter(service_id=self.service_id).exists():
                self.service_id = f"SRV{str(uuid.uuid4())[:8]}".upper()
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.service_id})"
        
    def image_url(self):
        """Return the URL of the image or a default image if none exists"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/img/default-service.jpg'  # Path to a default image

class Discount(AuditableMixin, models.Model):
    discount_id = models.CharField(max_length=15, unique=True, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[discount_validator])
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    
    def save(self, *args, **kwargs):
        if not self.discount_id:
            # Create a unique ID based on UUID
            self.discount_id = f"DSC{str(uuid.uuid4())[:8]}".upper()
            
            # Ensure the ID is unique (extremely unlikely to be needed, but added for safety)
            while Discount.objects.filter(discount_id=self.discount_id).exists():
                self.discount_id = f"DSC{str(uuid.uuid4())[:8]}".upper()
        
        super().save(*args, **kwargs)
    
    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date
    
    def is_upcoming(self):
        now = timezone.now()
        return now < self.start_date
    
    def is_expired(self):
        now = timezone.now()
        return now > self.end_date
    
    def total_usage(self):
        """Count how many times this discount has been applied to bookings"""
        return self.applied_bookings.count()
    
    def total_savings(self):
        """Calculate total amount saved through this discount"""
        savings = 0
        for booking in self.applied_bookings.all():
            original_price = booking.service.price
            savings += (original_price * self.percentage / 100)
        return savings
    
    def __str__(self):
        return f"{self.service.name} {self.percentage}% ({self.discount_id})"
    


class Booking(AuditableMixin, models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    booking_id = models.CharField(max_length=15, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    custom_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[discount_validator])
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, related_name='created_bookings', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(CustomUser, related_name='updated_bookings', on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    service_discount = models.ForeignKey(
        Discount, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='applied_bookings'
    )
    therapist = models.ForeignKey(
    CustomUser,
    related_name='assigned_bookings',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    limit_choices_to={'user_type': 'STAFF'}
    )

    
    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = f"BKG{str(uuid.uuid4())[:8]}".upper()
            
            while Booking.objects.filter(booking_id=self.booking_id).exists():
                self.booking_id = f"BKG{str(uuid.uuid4())[:8]}".upper()
        
        super().save(*args, **kwargs)
    
    def get_final_price(self):
        price = self.service.price
        
        # Check for active service discounts at the time of booking
        active_discounts = Discount.objects.filter(
            service=self.service,
            start_date__lte=self.date_time,
            end_date__gte=self.date_time
        ).order_by('-percentage')  # Get highest discount if multiple exist
        
        # Apply service time-based discount if available
        if active_discounts.exists():
            service_discount = active_discounts.first()
            self.service_discount = service_discount  # Store reference to the applied discount
            discounted_price = price * (1 - service_discount.percentage / 100)
            price = discounted_price
        
        # Apply customer-specific discount if available
        if self.custom_discount > 0:
            custom_discounted_price = price * (1 - self.custom_discount / 100)
            price = custom_discounted_price
        
        return price
    
    def get_expected_start_time(self):
        """
        Calculate the expected start time for this booking based on:
        1. Booking's scheduled time
        2. Other bookings scheduled before this one
        3. Duration of those services
        """
        from django.utils import timezone
        
        # If the booking is already completed or cancelled, return the original booking time
        if self.status in ['COMPLETED', 'CANCELLED']:
            return self.date_time
        
        # Get all pending and confirmed bookings for the same day up to this booking's time
        booking_date = self.date_time.date()
        earlier_bookings = Booking.objects.filter(
            date_time__date=booking_date,
            date_time__lt=self.date_time,
            status__in=['PENDING', 'CONFIRMED']
        ).order_by('date_time')
        
        # If there are no earlier bookings, the expected start time is the scheduled time
        if not earlier_bookings.exists():
            return self.date_time
        
        # Calculate when each earlier booking will end
        latest_end_time = self.date_time  # Default to scheduled time
        
        for booking in earlier_bookings:
            # Calculate when this booking is expected to end
            booking_end_time = booking.date_time + timezone.timedelta(minutes=booking.service.duration)
            
            # If this booking ends after our current booking's scheduled start time,
            # adjust our expected start time
            if booking_end_time > latest_end_time:
                latest_end_time = booking_end_time
        
        return latest_end_time
    def get_total_price(self):
        """Calculate total price including main service and additional services"""
        main_service_price = self.get_final_price()
        
        # Get additional services
        additional_services = self.additional_services.all()
        additional_services_total = sum(service.final_price for service in additional_services)
        
        return main_service_price + additional_services_total
    def get_wait_time_minutes(self):
        """Calculate the wait time in minutes from scheduled time to expected start time"""
        expected_start = self.get_expected_start_time()
        if expected_start > self.date_time:
            wait_time = expected_start - self.date_time
            return int(wait_time.total_seconds() / 60)
        return 0
    
    def __str__(self):
        return f"{self.booking_id} - {self.customer.first_name} - {self.service.name}"



class Sale(AuditableMixin, models.Model):
    sale_id = models.CharField(max_length=15, unique=True, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    payment_date = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    payment_discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0, 
        validators=[discount_validator],
        help_text="Additional discount applied at payment time"
    )
    
    def save(self, *args, **kwargs):
        if not self.sale_id:
            # Create a unique ID based on UUID
            self.sale_id = f"SLE{str(uuid.uuid4())[:8]}".upper()
            
            # Ensure the ID is unique
            while Sale.objects.filter(sale_id=self.sale_id).exists():
                self.sale_id = f"SLE{str(uuid.uuid4())[:8]}".upper()
                    
        # Generate receipt number if it doesn't exist
        if not self.receipt_number:
            from django.db import transaction
            
            # Use a transaction with select_for_update to prevent race conditions
            with transaction.atomic():
                today = timezone.now().strftime('%Y%m%d')
                receipt_prefix = f"RCP{today}-"
                
                # Lock the rows we're querying to prevent concurrent access
                last_receipt = Sale.objects.filter(
                    receipt_number__startswith=receipt_prefix
                ).order_by('-receipt_number').select_for_update().first()
                
                if last_receipt and last_receipt.receipt_number:
                    try:
                        # Extract the sequence number and increment it
                        seq_str = last_receipt.receipt_number.split('-')[1]
                        seq = int(seq_str) + 1
                    except (IndexError, ValueError):
                        seq = 1
                else:
                    seq = 1
                
                # Generate the new receipt number
                self.receipt_number = f"{receipt_prefix}{seq:03d}"
                
                # Double-check that this receipt number isn't already used
                while Sale.objects.filter(receipt_number=self.receipt_number).exists():
                    seq += 1
                    self.receipt_number = f"{receipt_prefix}{seq:03d}"
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.sale_id} - {self.booking.customer.first_name} - {self.payment_amount}"
    


class ServiceImage(AuditableMixin, models.Model):
    service = models.ForeignKey(Service, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='service_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"Image for {self.service.name}"
        
    def image_url(self):
        """Return the URL of the image or a default image if none exists"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/img/default-service.jpg'
    

class AdditionalService(AuditableMixin, models.Model):
    # Primary relationships - can be linked to either booking or sale
    booking = models.ForeignKey(Booking, related_name='additional_services', 
                               on_delete=models.CASCADE, null=True, blank=True)
    sale = models.ForeignKey(Sale, related_name='additional_services', 
                            on_delete=models.CASCADE, null=True, blank=True)
    
    # Service details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    regular_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Meta information
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    therapist = models.ForeignKey(
    CustomUser,
    related_name='assigned_additional_services',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    limit_choices_to={'user_type': 'STAFF'}
    )
    
    class Meta:
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        # Auto-calculate final_price if not explicitly set
        if not self.final_price and self.regular_price and self.discount_percentage:
            self.final_price = self.regular_price * (1 - self.discount_percentage / 100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - GHS{self.final_price}"
    



class Audit(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255)
    data = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    # Add these new fields:
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    message = models.TextField(blank=True, null=True)







class BookingRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    request_id = models.CharField(max_length=15, unique=True, editable=False)
    # Customer information fields - these will be used if the customer is new
    is_new_customer = models.BooleanField(default=False)
    existing_customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Service and time information
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    
    # Additional services as a JSON field
    additional_services = models.JSONField(blank=True, null=True)
    
    # Request status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For tracking which staff member reviewed the request
    reviewed_by = models.ForeignKey(CustomUser, related_name='reviewed_requests', 
                                   on_delete=models.SET_NULL, null=True, blank=True)
    
    preferred_therapist = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='preferred_booking_requests'
    )
    
    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = f"REQ{str(uuid.uuid4())[:8]}".upper()
            
            while BookingRequest.objects.filter(request_id=self.request_id).exists():
                self.request_id = f"REQ{str(uuid.uuid4())[:8]}".upper()
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.is_new_customer:
            return f"{self.request_id} - {self.first_name} {self.last_name} - {self.service.name}"
        elif self.existing_customer:
            return f"{self.request_id} - {self.existing_customer.first_name} {self.existing_customer.last_name} - {self.service.name}"
        else:
            return f"{self.request_id} - {self.service.name}"
        

# class BookingTherapist(models.Model):
#     booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='therapist_assignments')
#     therapist = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='booking_assignments')
#     service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
#     is_primary = models.BooleanField(default=True)
#     assigned_at = models.DateTimeField(auto_now_add=True)
#     assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='therapist_assignments_made')
    
#     class Meta:
#         unique_together = ('booking', 'therapist', 'service')
        
#     def __str__(self):
#         return f"{self.therapist.get_full_name()} - {self.booking.booking_id}"
    

class ServiceTherapist(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='assigned_therapists')
    therapist = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='assigned_services')
    is_primary = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('service', 'therapist')
        
    def __str__(self):
        return f"{self.therapist.get_full_name()} - {self.service.name}"


# Add to models.py or modify existing models

class BookingTherapistAssignment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='therapist_assignments')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    therapist = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='booking_assignments')
    is_primary = models.BooleanField(default=True, help_text="Whether this therapist is the primary provider for the booking")
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='assigned_therapists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('booking', 'therapist')
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"{self.booking.booking_id} - {self.therapist.get_full_name()}"
# class ServiceTherapist(models.Model):
#     service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='therapists')
#     therapist = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='services',
#                                  limit_choices_to={'user_type': 'STAFF'})
#     is_primary = models.BooleanField(default=False)
#     active = models.BooleanField(default=True)
    
#     class Meta:
#         unique_together = ('service', 'therapist')
        
#     def __str__(self):
#         return f"{self.therapist.get_full_name()} - {self.service.name}"