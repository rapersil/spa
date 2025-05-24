from django.views.generic import ListView, DetailView, CreateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Sum, Count, Q
from django.db import transaction
from django.utils import timezone
import csv
from datetime import datetime, timedelta
import json
from decimal import Decimal
from ..models import Sale, Booking, Service, AdditionalService
from ..forms import SaleForm, SalesReportForm, SaleSearchForm
from ..permissions import AdminRequiredMixin, StaffRequiredMixin

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import qrcode
import base64
import io
from io import BytesIO
from decimal import Decimal
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from ..models import Sale
from ..permissions import StaffRequiredMixin


class SaleListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 10

    def get_queryset(self):
        queryset = Sale.objects.all().order_by('-payment_date')

        # Get filter parameters from form
        form = SaleSearchForm(self.request.GET)
        if form.is_valid():
            query = form.cleaned_data.get('query')
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            payment_method = form.cleaned_data.get('payment_method')
            min_amount = form.cleaned_data.get('min_amount')
            max_amount = form.cleaned_data.get('max_amount')

            # Apply filters if provided
            if query:
                queryset = queryset.filter(
                    Q(receipt_number__icontains=query) |
                    Q(booking__customer__first_name__icontains=query) |
                    Q(booking__customer__last_name__icontains=query) |
                    Q(booking__service__name__icontains=query) |
                    Q(sale_id__iexact=query)
                )

            if start_date:
                queryset = queryset.filter(payment_date__date__gte=start_date)

            if end_date:
                queryset = queryset.filter(payment_date__date__lte=end_date)

            if payment_method:
                queryset = queryset.filter(payment_method=payment_method)

            if min_amount:
                queryset = queryset.filter(payment_amount__gte=min_amount)

            if max_amount:
                queryset = queryset.filter(payment_amount__lte=max_amount)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add search form to context
        context['search_form'] = SaleSearchForm(self.request.GET or None)

        # Get the current date
        today = timezone.now().date()

        # Calculate start dates for week and month
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Today's sales
        today_sales_queryset = Sale.objects.filter(payment_date__date=today)
        today_sales = {
            'total': today_sales_queryset.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0,
            'count': today_sales_queryset.count()
        }

        # This week's sales
        week_sales_queryset = Sale.objects.filter(payment_date__date__gte=week_start, payment_date__date__lte=today)
        week_sales = {
            'total': week_sales_queryset.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0,
            'count': week_sales_queryset.count()
        }

        # This month's sales
        month_sales_queryset = Sale.objects.filter(payment_date__date__gte=month_start, payment_date__date__lte=today)
        month_sales = {
            'total': month_sales_queryset.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0,
            'count': month_sales_queryset.count()
        }

        # Add to context
        context['today_sales'] = today_sales
        context['week_sales'] = week_sales
        context['month_sales'] = month_sales

        return context


class SaleDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Sale
    template_name = 'sales/sale_detail.html'
    context_object_name = 'sale'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sale = self.get_object()
        booking = sale.booking

        # Add existing service discount and custom discount calculations
        if booking.service_discount:
            service_discount_amount = booking.service.price * (booking.service_discount.percentage / 100)
            context['service_discount_amount'] = service_discount_amount

            if booking.custom_discount > 0:
                # Custom discount applies to price after service discount
                price_after_service_discount = booking.service.price - service_discount_amount
                context['custom_discount_amount'] = price_after_service_discount * (booking.custom_discount / 100)
        elif booking.custom_discount > 0:
            # Only custom discount
            context['custom_discount_amount'] = booking.service.price * (booking.custom_discount / 100)

        # Add additional services
        additional_services = sale.additional_services.all()
        context['additional_services'] = additional_services

        # Calculate total amount for additional services
        if additional_services.exists():
            context['additional_services_total'] = sum(service.final_price for service in additional_services)

        return context


class SaleCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'
    success_url = reverse_lazy('sales_list')

    # def __init__(self, **kwargs):
    #     super().__init__(kwargs)
    #     self.object = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking_id = self.request.GET.get('booking_id')

        if booking_id:
            selected_booking = get_object_or_404(Booking, pk=booking_id)
            context['selected_booking'] = selected_booking

            # Add existing custom discount info for display
            if selected_booking.custom_discount > 0:
                context['has_existing_discount'] = True
                context['existing_discount'] = selected_booking.custom_discount

            # Add existing additional services
            context['existing_additional_services'] = AdditionalService.objects.filter(booking=selected_booking)

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # If booking_id is in GET params, pre-select booking
        booking_id = self.request.GET.get('booking_id')
        if booking_id:
            booking = get_object_or_404(Booking, pk=booking_id)

            # Calculate total price including additional services
            booking_price = booking.get_final_price()
            additional_services = AdditionalService.objects.filter(booking=booking)
            additional_total = sum(service.final_price for service in additional_services)
            total_price = booking_price + additional_total

            # Initialize with booking and its total price
            initial_data = {
                'booking': booking,
                'payment_amount': total_price,
                'payment_discount': 0  # Start with 0 payment discount
            }

            kwargs['initial'] = initial_data

        return kwargs

    def form_valid(self, form):
        # Begin a transaction to ensure everything is saved properly
        with transaction.atomic():
            # Save the user who created this sale
            form.instance.created_by = self.request.user
            booking = form.cleaned_data['booking']
            payment_discount = form.cleaned_data.get('payment_discount') or 0

            # Parse additional services from JSON (for any new services added at sale time)
            additional_services_json = self.request.POST.get('additional_services', '[]')
            try:
                new_additional_services = json.loads(additional_services_json)
            except json.JSONDecodeError:
                new_additional_services = []

            # Get existing additional services from booking
            existing_services = AdditionalService.objects.filter(booking=booking)

            # Calculate the subtotal (booking price + additional services)
            booking_price = booking.get_final_price()
            existing_services_amount = sum(Decimal(str(service.final_price)) for service in existing_services)

            # Convert float values to Decimal for consistent arithmetic
            new_additional_amount = sum(
                Decimal(str(service.get('finalPrice', 0))) for service in new_additional_services)
            subtotal = booking_price + existing_services_amount + new_additional_amount

            # Apply payment discount if provided
            if payment_discount > 0:
                discount_amount = subtotal * (Decimal(str(payment_discount)) / Decimal('100'))
                form.instance.payment_amount = subtotal - discount_amount
            else:
                form.instance.payment_amount = subtotal

            # Update booking status to completed if not already
            if booking.status != 'COMPLETED':
                booking.status = 'COMPLETED'
                booking.updated_by = self.request.user
                booking.save()

            # Save the form but don't return yet
            self.object = form.save()

            # Update existing AdditionalService records to link to this sale
            for service in existing_services:
                service.sale = self.object
                service.save()

            # Now create new AdditionalService records for any added at sale time
            for service in new_additional_services:
                AdditionalService.objects.create(
                    sale=self.object,
                    booking=booking,  # Link to both sale and booking
                    name=service.get('name', ''),
                    description=service.get('description', ''),
                    regular_price=Decimal(str(service.get('regularPrice', 0))),
                    discount_percentage=Decimal(str(service.get('discountPercentage', 0))),
                    final_price=Decimal(str(service.get('finalPrice', 0))),
                    created_by=self.request.user
                )

            messages.success(self.request, "Sale recorded successfully with all additional services.")

            # Let the parent handle the redirect
            return super(SaleCreateView, self).form_valid(form)


class SalesReportView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = 'sales/sales_report.html'

    def get(self, request):
        # Default to current month
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today

        form = SalesReportForm(initial={
            'start_date': start_date,
            'end_date': end_date,
        })

        return render(request, self.template_name, {
            'form': form,
        })

    def post(self, request):
        form = SalesReportForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            service = form.cleaned_data.get('service')

            # Base queryset
            sales = Sale.objects.filter(
                payment_date__date__gte=start_date,
                payment_date__date__lte=end_date
            )

            # Filter by service if selected
            if service:
                sales = sales.filter(booking__service=service)

            # Basic statistics
            total_sales = sales.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
            sales_count = sales.count()

            # Sales by service
            sales_by_service = Service.objects.filter(
                booking__sale__in=sales
            ).annotate(
                total_amount=Sum('booking__sale__payment_amount'),
                sales_count=Count('booking__sale')
            ).order_by('-total_amount')

            # Sales by day
            days = (end_date - start_date).days + 1
            sales_by_day = []

            for i in range(days):
                day = start_date + timedelta(days=i)

                day_sales = sales.filter(payment_date__date=day)
                day_total = day_sales.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
                day_count = day_sales.count()

                sales_by_day.append({
                    'date': day,
                    'total': day_total,
                    'count': day_count
                })

            context = {
                'form': form,
                'total_sales': total_sales,
                'sales_count': sales_count,
                'sales_by_service': sales_by_service,
                'sales_by_day': sales_by_day,
                'start_date': start_date,
                'end_date': end_date,
                'service': service,
                'report_generated': True
            }

            # Check if export requested
            if 'export' in request.POST:
                return self.export_csv(sales, start_date, end_date, service)

            return render(request, self.template_name, context)

        return render(request, self.template_name, {'form': form})

    def export_csv(self, sales, start_date, end_date, service=None):
        response = HttpResponse(content_type='text/csv')
        filename = f"sales_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Date', 'Receipt', 'Customer', 'Service', 'Payment Method', 'Amount'])

        for sale in sales.order_by('payment_date'):
            writer.writerow([
                sale.payment_date.strftime('%Y-%m-%d %H:%M'),
                sale.receipt_number,
                f"{sale.booking.customer.first_name} {sale.booking.customer.last_name}",
                sale.booking.service.name,
                sale.payment_method,
                sale.payment_amount
            ])

        return response


# In sales_views.py
class SalePrintView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'sales/payment_receipt.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sale_id = self.kwargs.get('pk')
        sale = get_object_or_404(Sale, pk=sale_id)
        booking = sale.booking

        # Add sale to context
        context['sale'] = sale

        # Explicitly add the service discount object to context
        context['service_discount'] = booking.service_discount

        # Calculate service discount amount if applicable
        if booking.service_discount:
            service_discount_amount = booking.service.price * (booking.service_discount.percentage / 100)
            context['service_discount_amount'] = service_discount_amount

            if booking.custom_discount > 0:
                # Custom discount applies to price after service discount
                price_after_service_discount = booking.service.price - service_discount_amount
                context['custom_discount_amount'] = price_after_service_discount * (booking.custom_discount / 100)
        elif booking.custom_discount > 0:
            # Only custom discount
            context['custom_discount_amount'] = booking.service.price * (booking.custom_discount / 100)

        # Calculate payment discount if applicable
        if hasattr(sale, 'payment_discount') and sale.payment_discount > 0:
            price_after_previous_discounts = booking.get_final_price()
            context['payment_discount_amount'] = price_after_previous_discounts * (sale.payment_discount / 100)

        # Add additional services
        additional_services = sale.additional_services.all()
        context['additional_services'] = additional_services

        # Calculate total amount for additional services
        if additional_services.exists():
            context['additional_services_total'] = sum(service.final_price for service in additional_services)

        # Generate QR code with receipt verification data
        verification_text = (
            f"ID:{sale.receipt_number}\n"
            f"Customer:{booking.customer.first_name} {booking.customer.last_name}\n"
            f"Service:{booking.service.name}\n"
            f"Date:{sale.payment_date.strftime('%Y-%m-%d')}\n"
            f"Amount:GHS{sale.payment_amount}\n"
        )

        # Generate QR code with higher error correction level
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(verification_text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64 string for embedding in HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

        context['qr_code'] = img_str

        return context
