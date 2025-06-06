# Generated by Django 5.2 on 2025-05-11 15:22

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beauty_app', '0021_customuser_primary_service_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingServiceAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary', models.BooleanField(default=False, help_text='Whether this is the primary service of the booking')),
                ('is_additional', models.BooleanField(default=False, help_text='Whether this is an additional service')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assignments_made', to=settings.AUTH_USER_MODEL)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_assignments', to='beauty_app.booking')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='beauty_app.service')),
                ('therapist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_assignments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('booking', 'service', 'therapist')},
            },
        ),
    ]
