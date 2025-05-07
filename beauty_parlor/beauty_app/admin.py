# beauty_app/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Customer, Service, Booking, Discount, Sale, ServiceImage,AdditionalService,Audit

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'user_id', 'first_name', 'last_name', 'user_type', 'is_active')
    list_filter = ('user_type', 'is_active', 'date_joined')
    search_fields = ('username', 'user_id', 'first_name', 'last_name', 'phone_number')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture', 'password_change_required')}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'phone_number', 'user_type'),
        }),
    )
    
    readonly_fields = ('user_id', 'last_login', 'date_joined')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'full_name', 'phone', 'date_joined', 'created_by')
    list_filter = ('date_joined', 'created_by')
    search_fields = ('customer_id', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('Customer Information', {'fields': ('customer_id', 'first_name', 'last_name', 'phone')}),
        ('Additional Information', {'fields': ('address', 'notes')}),
        ('System Information', {'fields': ('date_joined', 'created_by')}),
    )
    
    readonly_fields = ('customer_id', 'date_joined')
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'



class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 3
    fields = ('image', 'caption', 'order')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('service_id', 'name', 'price', 'duration', 'active', 'service_image')
    list_filter = ('active',)
    search_fields = ('service_id', 'name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Service Information', {'fields': ('service_id', 'name', 'description', 'image')}),
        ('Pricing & Duration', {'fields': ('price', 'duration')}),
        ('Status', {'fields': ('active',)}),
    )
    
    readonly_fields = ('service_id',)
    inlines = [ServiceImageInline]
    
    def service_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "No Image"
    service_image.short_description = 'Image'

class DiscountInline(admin.TabularInline):
    model = Discount
    extra = 0
    fields = ('percentage', 'start_date', 'end_date', 'created_by')
    readonly_fields = ('created_by',)
    
    def has_add_permission(self, request, obj=None):
        return True
    
    def has_delete_permission(self, request, obj=None):
        return True

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('discount_id', 'service', 'percentage', 'start_date', 'end_date', 'discount_status', 'created_by')
    list_filter = ('service', 'created_by', 'start_date', 'end_date')
    search_fields = ('discount_id', 'service__name')
    ordering = ('-start_date',)
    
    fieldsets = (
        ('Discount Information', {'fields': ('discount_id', 'service', 'percentage')}),
        ('Validity Period', {'fields': ('start_date', 'end_date')}),
        ('System Information', {'fields': ('created_by',)}),
    )
    
    readonly_fields = ('discount_id',)
    
    def discount_status(self, obj):
        from django.utils import timezone
        now = timezone.now()
        
        if obj.start_date <= now <= obj.end_date:
            return format_html('<span style="color: green; font-weight: bold;">Active</span>')
        elif obj.start_date > now:
            return format_html('<span style="color: blue;">Upcoming</span>')
        else:
            return format_html('<span style="color: grey;">Expired</span>')
    
    discount_status.short_description = 'Status'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'customer_name', 'service_name', 'date_time', 'status', 'final_price', 'created_by')
    list_filter = ('status', 'date_time', 'service', 'created_by')
    search_fields = ('booking_id', 'customer__first_name', 'customer__last_name', 'service__name')
    ordering = ('-date_time',)
    
    fieldsets = (
        ('Booking Information', {'fields': ('booking_id', 'customer', 'service', 'date_time', 'status')}),
        ('Pricing', {'fields': ('custom_discount', 'get_final_price')}),
        ('Additional Information', {'fields': ('notes',)}),
        ('System Information', {'fields': ('created_by', 'created_at', 'updated_by', 'updated_at')}),
    )
    
    readonly_fields = ('booking_id', 'get_final_price', 'created_at', 'updated_at')
    
    def customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"
    customer_name.short_description = 'Customer'
    
    def service_name(self, obj):
        return obj.service.name
    service_name.short_description = 'Service'
    
    def final_price(self, obj):
        return f"${obj.get_final_price()}"
    final_price.short_description = 'Price'
    
    def get_final_price(self, obj):
        return f"${obj.get_final_price()}"
    get_final_price.short_description = 'Final Price (After Discounts)'

class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ('booking_id', 'service', 'date_time', 'status')
    readonly_fields = ('booking_id',)
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_id', 'receipt_number', 'customer_name', 'service_name', 'payment_date', 'payment_amount', 'payment_method', 'created_by')
    list_filter = ('payment_method', 'payment_date', 'created_by')
    search_fields = ('sale_id', 'receipt_number', 'booking__customer__first_name', 'booking__customer__last_name')
    ordering = ('-payment_date',)
    
    fieldsets = (
        ('Sale Information', {'fields': ('sale_id', 'receipt_number', 'booking')}),
        ('Payment Details', {'fields': ('payment_amount', 'payment_method', 'payment_date')}),
        ('System Information', {'fields': ('created_by',)}),
    )
    
    readonly_fields = ('sale_id', 'receipt_number', 'payment_date')
    
    def customer_name(self, obj):
        return f"{obj.booking.customer.first_name} {obj.booking.customer.last_name}"
    customer_name.short_description = 'Customer'
    
    def service_name(self, obj):
        return obj.booking.service.name
    service_name.short_description = 'Service'


admin.site.register(AdditionalService)


# Add to beauty_app/admin.py

@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'object_repr', 'ip_address')
    list_filter = ('action', 'model_name', 'timestamp', 'user')
    search_fields = ('object_id', 'object_repr', 'user__username')
    readonly_fields = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'object_repr', 'data', 'ip_address')
    date_hierarchy = 'timestamp'