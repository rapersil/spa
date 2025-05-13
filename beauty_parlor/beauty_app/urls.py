# beauty_app/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView


from .views.auth_views import (
    CustomLoginView, logout_view, CustomPasswordChangeView,
    PasswordChangeRequiredView, AdminPasswordResetListView, AdminPasswordResetView
)
from .views.dashboard_views import DashboardView, AdminDashboardView
from .views.customer_views import (
    CustomerListView, CustomerDetailView, CustomerCreateView, CustomerUpdateView
)
from .views.service_views import (
    ServiceListView, ServiceDetailView, ServiceCreateView, ServiceUpdateView,check_service_discount,ServiceImageDeleteView,PublicLandingView
    ,PublicServiceListView,PublicServiceDetailView
)
from .views.booking_views import (
    BookingListView, BookingDetailView, BookingCreateView, BookingUpdateView, 
    BookingDeleteView, BookingStatusUpdateView, BookingPrintView,booking_calendar_view,public_booking_calendar_view
)
from .views.discount_views import (
    DiscountListView, DiscountDetailView, DiscountCreateView, DiscountUpdateView, DiscountDeleteView,ServiceDiscountHistoryView
)
from .views.sales_views import (
    SaleListView, SaleDetailView, SaleCreateView, SalesReportView,SalePrintView
)
from .views.user_views import (
    StaffListView, StaffDetailView, StaffCreateView, StaffUpdateView, ProfileView
)

from .views.booking_request_views import (
    PublicBookingRequestCreateView, PublicBookingRequestConfirmationView,
    StaffBookingRequestListView, StaffBookingRequestDetailView,
    StaffBookingRequestApproveView, StaffBookingRequestRejectView
)
from .views.therapist_views import TherapistAssignmentView, RemoveTherapistAssignmentView  # Import the missing views
from .views.api_views import therapists_for_service
from .views.session_views import keep_session_alive




urlpatterns = [
    # Authentication URLs
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change-required/', PasswordChangeRequiredView.as_view(), name='password_change_required'),
    
    # Admin Password Reset URLs
    path('password-reset/', AdminPasswordResetListView.as_view(), name='password_reset_list'),
    path('password-reset/<int:pk>/', AdminPasswordResetView.as_view(), name='password_reset'),
    
    
    # Dashboard URLs
    path('', DashboardView.as_view(), name='dashboard'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Customer URLs
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/new/', CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer_update'),
    
    # Service URLs
    path('services/', ServiceListView.as_view(), name='service_list'),
    path('services/new/', ServiceCreateView.as_view(), name='service_create'),
    path('services/<int:pk>/', ServiceDetailView.as_view(), name='service_detail'),
    path('services/<int:pk>/edit/', ServiceUpdateView.as_view(), name='service_update'),
    path('services/<int:service_id>/images/<int:image_id>/delete/', ServiceImageDeleteView.as_view(), name='service_image_delete'),    
    # Booking URLs
    path('bookings/', BookingListView.as_view(), name='booking_list'),
    path('bookings/new/', BookingCreateView.as_view(), name='booking_create'),
    path('bookings/<int:pk>/', BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/<int:pk>/edit/', BookingUpdateView.as_view(), name='booking_update'),
    path('bookings/<int:pk>/delete/', BookingDeleteView.as_view(), name='booking_delete'),
    path('bookings/<int:pk>/status/', BookingStatusUpdateView.as_view(), name='booking_status_update'),
    # Add this to urlpatterns in urls.py
    path('bookings/<int:pk>/print/', BookingPrintView.as_view(), name='booking_print'),
    path('bookings/calendar/', booking_calendar_view, name='booking_calendar'),

    
    
    # Discount URLs
    path('discounts/', DiscountListView.as_view(), name='discount_list'),
    path('discounts/new/', DiscountCreateView.as_view(), name='discount_create'),
    path('discounts/<int:pk>/', DiscountDetailView.as_view(), name='discount_detail'),
    path('discounts/<int:pk>/edit/', DiscountUpdateView.as_view(), name='discount_update'),
    path('discounts/<int:pk>/delete/', DiscountDeleteView.as_view(), name='discount_delete'),
    
    # Sales URLs
    path('sales/', SaleListView.as_view(), name='sales_list'),
    path('sales/new/', SaleCreateView.as_view(), name='sale_create'),
    path('sales/<int:pk>/', SaleDetailView.as_view(), name='sale_detail'),
    path('sales/report/', SalesReportView.as_view(), name='sales_report'),
    path('sales/<int:pk>/print/', SalePrintView.as_view(), name='sale_print'),
    
    # Staff/User URLs
    path('staff/', StaffListView.as_view(), name='staff_list'),
    path('staff/new/', StaffCreateView.as_view(), name='staff_create'),
    path('staff/<int:pk>/', StaffDetailView.as_view(), name='staff_detail'),
    path('staff/<int:pk>/edit/', StaffUpdateView.as_view(), name='staff_update'),
    
    # Profile URL
    path('profile/', ProfileView.as_view(), name='profile'),


    path('services/<int:pk>/discounts/', ServiceDiscountHistoryView.as_view(), name='service_discount_history'),
    path('check-service-discount/', check_service_discount, name='check_service_discount'),
    path('api/keep-session-alive/', keep_session_alive, name='keep_session_alive'),


    # Public-facing URLs
    path('public/', PublicLandingView.as_view(), name='public_landing'),
    path('public/services/', PublicServiceListView.as_view(), name='public_service_list'),
    path('public/services/<int:pk>/', PublicServiceDetailView.as_view(), name='public_service_detail'),
    # Public booking calendar
    path('public/calendar/', public_booking_calendar_view, name='public_booking_calendar'),




    # Public booking request URLs
    path('request-booking/', PublicBookingRequestCreateView.as_view(), name='public_booking_request_create'),
    path('request-booking/<int:step>/', PublicBookingRequestCreateView.as_view(), name='public_booking_request_create'),
    path('request-booking/confirmation/<str:request_id>/', PublicBookingRequestConfirmationView.as_view(), name='public_booking_request_confirmation'),

    # Staff booking request URLs
    path('booking-requests/', StaffBookingRequestListView.as_view(), name='staff_booking_request_list'),
    path('booking-requests/<int:pk>/', StaffBookingRequestDetailView.as_view(), name='staff_booking_request_detail'),
    path('booking-requests/<int:pk>/approve/', StaffBookingRequestApproveView.as_view(), name='staff_booking_request_approve'),
    path('booking-requests/<int:pk>/reject/', StaffBookingRequestRejectView.as_view(), name='staff_booking_request_reject'),
    
    path('bookings/<int:booking_id>/assign-therapist/', TherapistAssignmentView.as_view(), name='assign_therapist'),
    path('therapist-assignment/<int:pk>/remove/', RemoveTherapistAssignmentView.as_view(), name='remove_therapist_assignment'),

    
    path('api/therapists-for-service/', therapists_for_service, name='therapists_for_service'),
        

    
]

# Add this at the end of the file
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)