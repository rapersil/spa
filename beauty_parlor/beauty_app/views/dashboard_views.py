# beauty_app/views/dashboard_views.py
from datetime import date as datetime_date, timedelta
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Count, Sum, Q
import calendar
from datetime import timedelta, datetime

from ..models import Booking, Customer, Sale, Service
from ..permissions import StaffRequiredMixin, AdminRequiredMixin


# beauty_app/views/dashboard_views.py


class DashboardView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        current_user = self.request.user
        # Get the selected view type from request (default to 'current')
        view_type = self.request.GET.get('view_type', 'current')
        current_only = (view_type == 'current')

        # Add view_type to context for template
        context['view_type'] = view_type

        # Today's bookings
        context['todays_bookings'] = Booking.objects.filter(
            date_time__date=today
        ).order_by('date_time')

        # Pending bookings (excluding today)
        context['pending_bookings'] = Booking.objects.filter(
            status='PENDING',
            date_time__date__gt=today
        ).order_by('date_time')[:5]

        # Recent customers
        context['recent_customers'] = Customer.objects.all().order_by('-date_joined')[:5]

        # Stats visible to all staff
        context['total_customers'] = Customer.objects.count()
        context['total_bookings_today'] = context['todays_bookings'].count()
        context['completed_bookings_today'] = context['todays_bookings'].filter(status='COMPLETED').count()

        # --- ENHANCED STAFF STATISTICS ---

        # 1. Personal Performance Metrics
        context['bookings_created_by_me'] = Booking.objects.filter(
            created_by=current_user
        ).count()

        context['bookings_created_today_by_me'] = Booking.objects.filter(
            created_by=current_user,
            created_at__date=today
        ).count()

        context['my_recent_bookings'] = Booking.objects.filter(
            created_by=current_user
        ).order_by('-created_at')[:5]

        # 2. Service Analytics with time toggle 
        last_30_days = today - timedelta(days=30)
        context['most_popular_services'] = self.get_popular_services(
            start_date=last_30_days,
            current_only=current_only
        )

        # 3. Booking Trends
        last_30_days = today - timedelta(days=30)
        context['booking_completion_rate'] = self.calculate_completion_rate(last_30_days, current_only)
        context['booking_cancellation_rate'] = self.calculate_cancellation_rate(last_30_days, current_only)
        context['booking_pending_rate'] = self.calculate_pending_rate(last_30_days, current_only)
        context['booking_confirmed_rate'] = self.calculate_confirmed_rate(last_30_days, current_only)

        # Bookings by weekday
        context['bookings_by_weekday'] = self.get_bookings_by_weekday(last_30_days)

        # 4. Customer Insights
        context['new_customers_this_month'] = Customer.objects.filter(
            date_joined__gte=today.replace(day=1)
        ).count()

        context['returning_customers'] = self.get_returning_customers()

        # 5. Scheduling Insights
        next_7_days = today + timedelta(days=7)
        context['upcoming_week_bookings'] = Booking.objects.filter(
            date_time__date__gt=today,
            date_time__date__lte=next_7_days,
            status__in=['CONFIRMED', 'PENDING']
        ).count()

        context['free_time_slots'] = self.calculate_free_slots(next_7_days)

        # Admin-only statistics
        if self.request.user.user_type in ['ADMIN', 'SUPERADMIN']:
            # Sales data for today
            today_sales = Sale.objects.filter(payment_date__date=today)
            context['total_sales_today'] = today_sales.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
            context['sales_count_today'] = today_sales.count()

            # This month data
            first_day = today.replace(day=1)
            last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

            month_sales = Sale.objects.filter(payment_date__date__range=[first_day, last_day])

            context['total_sales_month'] = month_sales.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
            context['sales_count_month'] = month_sales.count()

            # Popular services
            context['popular_services'] = Service.objects.filter(booking__status='COMPLETED').annotate(
                booking_count=Count('booking')
            ).order_by('-booking_count')[:5]

            # Weekly chart data - last 7 days sales
            weekly_data = []
            for i in range(6, -1, -1):
                date_point = today - timedelta(days=i)
                daily_sales = Sale.objects.filter(payment_date__date=date_point)
                daily_amount = daily_sales.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
                weekly_data.append({
                    'date': date_point.strftime('%a'),
                    'amount': float(daily_amount)
                })
            context['weekly_data'] = weekly_data

            # Monthly chart data - last 12 months
            # Monthly chart data - current year by month
            monthly_data = []
            current_year = today.year

            for month in range(1, 13):
                # Create date objects for the first and last day of each month
                start_date = datetime_date(current_year, month, 1)
                # Get the last day of the month
                last_day = calendar.monthrange(current_year, month)[1]
                end_date = datetime_date(current_year, month, last_day)

                # For future months, skip or show zero
                if start_date > today:
                    monthly_data.append({
                        'date': start_date.strftime('%b'),
                        'amount': 0
                    })
                    continue

                # For the current month, only include data up to today
                if month == today.month:
                    end_date = today

                # Get sales for this month
                monthly_sales = Sale.objects.filter(
                    payment_date__date__range=[start_date, end_date]
                )
                monthly_amount = monthly_sales.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0

                monthly_data.append({
                    'date': start_date.strftime('%b'),
                    'amount': float(monthly_amount)
                })

            context['monthly_data'] = monthly_data

            # Yearly chart data - last 5 years
            yearly_data = []
            current_year = today.year
            for i in range(4, -1, -1):
                year = current_year - i
                # Use the aliased datetime_date here
                start_date = datetime_date(year, 1, 1)
                end_date = datetime_date(year, 12, 31)

                if end_date > today:
                    end_date = today

                yearly_sales = Sale.objects.filter(
                    payment_date__date__range=[start_date, end_date]
                )
                yearly_amount = yearly_sales.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0

                yearly_data.append({
                    'date': str(year),
                    'amount': float(yearly_amount)
                })
            context['yearly_data'] = yearly_data

        return context

    def calculate_completion_rate(self, start_date, current_only=True):
        """Calculate the percentage of bookings that were completed successfully"""
        query = Q(date_time__date__gte=start_date, status__in=['COMPLETED', 'CANCELLED', 'CONFIRMED', 'PENDING'])

        # Only add the date filter if current_only is True
        if current_only:
            query &= Q(date_time__date__lt=timezone.now().date())

        total_bookings = Booking.objects.filter(query).count()

        if total_bookings == 0:
            return 0  # Fixed: Return 0% when no bookings exist

        # Apply the same current_only logic to completed bookings query
        completed_query = Q(date_time__date__gte=start_date, status='COMPLETED')
        if current_only:
            completed_query &= Q(date_time__date__lt=timezone.now().date())

        completed_bookings = Booking.objects.filter(completed_query).count()

        return int((completed_bookings / total_bookings) * 100)

    def calculate_cancellation_rate(self, start_date, current_only=True):
        """Calculate the percentage of bookings that were cancelled"""
        query = Q(date_time__date__gte=start_date, status__in=['COMPLETED', 'CANCELLED', 'CONFIRMED', 'PENDING'])

        if current_only:
            query &= Q(date_time__date__lt=timezone.now().date())

        total_bookings = Booking.objects.filter(query).count()

        if total_bookings == 0:
            return 0  # Correct: Return 0% when no bookings

        cancelled_query = Q(date_time__date__gte=start_date, status='CANCELLED')
        if current_only:
            cancelled_query &= Q(date_time__date__lt=timezone.now().date())

        cancelled_bookings = Booking.objects.filter(cancelled_query).count()

        return int((cancelled_bookings / total_bookings) * 100)

    def calculate_pending_rate(self, start_date, current_only=True):
        """Calculate the percentage of bookings that are pending"""
        query = Q(date_time__date__gte=start_date, status__in=['COMPLETED', 'CANCELLED', 'CONFIRMED', 'PENDING'])

        if current_only:
            query &= Q(date_time__date__lt=timezone.now().date())

        total_bookings = Booking.objects.filter(query).count()

        if total_bookings == 0:
            return 0  # Correct: Return 0% when no bookings

        pending_query = Q(date_time__date__gte=start_date, status='PENDING')
        if current_only:
            pending_query &= Q(date_time__date__lt=timezone.now().date())

        pending_bookings = Booking.objects.filter(pending_query).count()

        return int((pending_bookings / total_bookings) * 100)

    def calculate_confirmed_rate(self, start_date, current_only=True):
        """Calculate the percentage of bookings that are confirmed"""
        query = Q(date_time__date__gte=start_date, status__in=['COMPLETED', 'CANCELLED', 'CONFIRMED', 'PENDING'])

        if current_only:
            query &= Q(date_time__date__lt=timezone.now().date())

        total_bookings = Booking.objects.filter(query).count()

        if total_bookings == 0:
            return 0  # Correct: Return 0% when no bookings

        confirmed_query = Q(date_time__date__gte=start_date, status='CONFIRMED')
        if current_only:
            confirmed_query &= Q(date_time__date__lt=timezone.now().date())

        confirmed_bookings = Booking.objects.filter(confirmed_query).count()

        return int((confirmed_bookings / total_bookings) * 100)

    def get_popular_services(self, start_date=None, current_only=True):
        """Get most popular services with optional time filtering"""
        # Base query for completed or confirmed bookings
        query = Q(booking__status__in=['CONFIRMED', 'COMPLETED'])

        # Add date filtering if start_date is provided
        if start_date:
            print(f"Start date: {start_date}")
            date_query = Q(booking__date_time__date__gte=start_date)
            if current_only:
                date_query &= Q(booking__date_time__date__lt=timezone.now().date())
            query &= date_query

        # Get popular services
        return Service.objects.filter(
            query
        ).annotate(
            booking_count=Count('booking')
        ).order_by('-booking_count')[:5]

    def get_bookings_by_weekday(self, start_date):
        """Get distribution of bookings by day of week"""
        bookings = Booking.objects.filter(
            date_time__date__gte=start_date,
            status__in=['CONFIRMED', 'COMPLETED']
        )

        # Initialize counts for each day (0 = Monday, 6 = Sunday)
        weekday_counts = [0, 0, 0, 0, 0, 0, 0]

        for booking in bookings:
            weekday = booking.date_time.weekday()
            weekday_counts[weekday] += 1

        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        result = []
        for i, count in enumerate(weekday_counts):
            result.append({
                'name': weekday_names[i],
                'count': count
            })

        return result

    def get_returning_customers(self):
        """Get customers with multiple bookings"""
        return Customer.objects.annotate(
            booking_count=Count('booking')
        ).filter(
            booking_count__gt=1
        ).order_by('-booking_count')[:5]

    def calculate_free_slots(self, end_date):
        """Estimate number of available appointment slots in the next week"""
        # This is a simplified calculation
        # Assuming 8 working hours per day and average service duration of 60 minutes
        days_until_end = (end_date - timezone.now().date()).days

        # 8 hours * 60 minutes = 480 minutes per day
        # If average service is 60 minutes, that's about 8 slots per day
        total_slots = days_until_end * 8

        # Count existing bookings in the period
        booked_slots = Booking.objects.filter(
            date_time__date__gt=timezone.now().date(),
            date_time__date__lte=end_date,
            status__in=['CONFIRMED', 'PENDING']
        ).count()

        return max(0, total_slots - booked_slots)


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'dashboard/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # This view can be used for additional admin-specific dashboard content
        # that might be too detailed for the main dashboard
        return context
