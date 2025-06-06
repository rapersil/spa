# Generated by Django 5.2 on 2025-05-05 20:33

import beauty_app.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beauty_app', '0004_serviceimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='payment_discount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Additional discount applied at payment time', max_digits=5, validators=[beauty_app.validators.discount_validator]),
        ),
    ]
