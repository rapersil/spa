# Generated by Django 5.0.6 on 2025-05-22 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beauty_app', '0032_remove_discount_discount_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='discount',
            name='name',
            field=models.CharField(default='founders day promo', help_text="Discount campaign name (e.g., 'Christmas Bonus', 'Flash Sale')", max_length=100),
            preserve_default=False,
        ),
    ]
