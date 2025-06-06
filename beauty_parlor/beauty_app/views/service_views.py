# beauty_app/views/service_views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from ..models import Service, Discount, ServiceImage
from ..forms import ServiceForm
from ..permissions import StaffRequiredMixin, AdminRequiredMixin

from datetime import datetime
from django.utils import timezone

# Create your views here.
# Add this to your views.py
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.views import View


class ServiceListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Service
    template_name = 'service/service_list.html'
    context_object_name = 'services'
    paginate_by = 6  # Number of services per page

    def get_queryset(self):
        queryset = Service.objects.all().order_by('-active', 'name')

        # Apply search if provided
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(service_id__iexact=query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current timestamp
        from django.utils import timezone
        now = timezone.now()

        # Keep the original active_discounts for backward compatibility
        context['active_discounts'] = Discount.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        )

        # Add all current and upcoming discounts
        # This allows us to show both active and scheduled future discounts
        context['service_discounts'] = Discount.objects.filter(
            end_date__gte=now  # Only exclude expired discounts
        ).order_by('start_date')

        # Add flag to indicate if a discount is upcoming or active
        for discount in context['service_discounts']:
            discount.is_upcoming = discount.start_date > now

        return context


class ServiceDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Service
    template_name = 'service/service_detail.html'
    context_object_name = 'service'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add discounts for this service
        context['discounts'] = Discount.objects.filter(
            service=self.object
        ).order_by('-start_date')

        #get images for this service
        context['service_images'] = self.object.images.all()

        return context


class ServiceCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service/service_form.html'
    success_url = reverse_lazy('service_list')

    # def __init__(self, **kwargs):
    #     super().__init__(kwargs)
    #     self.object = None

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object = form.save()

        # Handle additional images
        images = self.request.FILES.getlist('additional_images')
        for i, image in enumerate(images):
            ServiceImage.objects.create(
                service=self.object,
                image=image,
                order=i + 1
            )

        messages.success(self.request, "Service created successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add note about the form requiring file upload
        context['multipart_form'] = True
        return context


class ServiceUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service/service_form.html'

    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.object = None

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object = form.save()

        # Handle additional images
        images = self.request.FILES.getlist('additional_images')
        for i, image in enumerate(images):
            # Get the current count of images to determine the order
            current_count = self.object.images.count()
            ServiceImage.objects.create(
                service=self.object,
                image=image,
                order=current_count + i + 1
            )

        messages.success(self.request, "Service updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('service_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add note about the form requiring file upload
        context['multipart_form'] = True
        # Add images for this service
        if self.object:
            context['additional_images'] = self.object.images.all()
        return context


class ServiceImageDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, service_id, image_id):
        service = get_object_or_404(Service, pk=service_id)
        image = get_object_or_404(ServiceImage, pk=image_id, service=service)
        image.delete()
        messages.success(request, "Image deleted successfully.")
        return redirect('service_detail', pk=service_id)


# Add this to your views.py
from django.http import JsonResponse


# def check_service_discount(request):
#     service_id = request.GET.get('service_id')
#     booking_date = request.GET.get('booking_date')

#     if not service_id or not booking_date:
#         return JsonResponse({'error': 'Missing parameters'}, status=400)

#     try:
#         service = Service.objects.get(id=service_id)
#         booking_datetime = datetime.fromisoformat(booking_date.replace('Z', '+00:00'))
#         print(service.price)

#         # Check for active discounts
#         discount = Discount.objects.filter(
#             service=service,
#             start_date__lte=booking_datetime,
#             end_date__gte=booking_datetime
#         ).order_by('-percentage').first()

#         if discount:
#             return JsonResponse({
#                 'discount_available': True,
#                 'discount_percentage': discount.percentage,
#                 'discount_id': discount.pk,
#                 'service_price': float(service.price),
#             })
#         else:
#             return JsonResponse({
#                 'discount_available': False,
#                 'service_price': float(service.price),  # Added service price even when no discount
#             })

#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)

# Add to your views (wherever check_service_discount is defined)
def check_service_discount(request):
    """Check if a service has active discounts for a given date"""
    service_id = request.GET.get('service_id')
    booking_date_str = request.GET.get('booking_date')

    if not service_id or not booking_date_str:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        service = Service.objects.get(pk=service_id)

        # Parse the datetime and make it timezone-aware
        try:
            # Try different formats
            for format_str in ['%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M', '%Y-%m-%d']:
                try:
                    naive_datetime = datetime.strptime(booking_date_str, format_str)
                    booking_date = timezone.make_aware(naive_datetime)
                    break
                except ValueError:
                    continue
            else:
                # If no format worked
                return JsonResponse({'error': 'Invalid date format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Date parsing error: {str(e)}'}, status=400)

        # Check for active discounts
        active_discount = Discount.objects.filter(
            service=service,
            start_date__lte=booking_date,
            end_date__gte=booking_date
        ).order_by('-percentage').first()

        if active_discount:
            return JsonResponse({
                'service_price': float(service.price),
                'discount_available': True,
                'discount_percentage': float(active_discount.percentage)
            })
        else:
            return JsonResponse({
                'service_price': float(service.price),
                'discount_available': False
            })

    except Service.DoesNotExist:
        return JsonResponse({'error': 'Service not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Add these imports if they're not already at the top
from django.views.generic import ListView, DetailView, TemplateView


# Add these new classes for public-facing views
class PublicServiceListView(ListView):
    model = Service
    template_name = 'service/public_service_list.html'
    context_object_name = 'services'
    paginate_by = 6

    def get_queryset(self):
        # Only show active services to the public
        queryset = Service.objects.filter(active=True).order_by('name')

        # Apply search if provided
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current timestamp
        from django.utils import timezone
        now = timezone.now()

        # Add active discounts to context
        context['active_discounts'] = Discount.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        )

        return context


class PublicServiceDetailView(DetailView):
    model = Service
    template_name = 'service/public_service_detail.html'
    context_object_name = 'service'

    def get_queryset(self):
        # Only show active services to the public
        return Service.objects.filter(active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add active discounts for this service
        from django.utils import timezone
        now = timezone.now()

        context['discounts'] = Discount.objects.filter(
            service=self.object,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-percentage')

        # Add service images
        context['service_images'] = self.object.images.all()

        return context


class PublicLandingView(TemplateView):
    template_name = 'public_landing_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current timestamp
        from django.utils import timezone
        now = timezone.now()

        # Add featured services (active services with images)
        context['featured_services'] = Service.objects.filter(
            active=True,
            image__isnull=False
        ).order_by('?')[:3]  # Random selection of 3 services

        # Add active discounts
        context['active_discounts'] = Discount.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        )

        return context
