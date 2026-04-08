from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('lands', '0007_land_size_payment_fields')]
    operations = [
        # Land pricing fields
        migrations.AddField(model_name='land', name='price_unit',
            field=models.CharField(max_length=10, default='month', blank=True,
                choices=[('month','Per Month'),('year','Per Year'),('total','Total / One-time')])),
        migrations.AddField(model_name='land', name='weekly_discount',
            field=models.DecimalField(max_digits=5, decimal_places=2, default=0)),
        migrations.AddField(model_name='land', name='monthly_discount',
            field=models.DecimalField(max_digits=5, decimal_places=2, default=0)),
        migrations.AddField(model_name='land', name='min_duration_days',
            field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name='land', name='max_duration_days',
            field=models.PositiveIntegerField(null=True, blank=True)),
        # Reservation date + pricing fields
        migrations.AddField(model_name='reservation', name='start_date',
            field=models.DateField(null=True, blank=True)),
        migrations.AddField(model_name='reservation', name='end_date',
            field=models.DateField(null=True, blank=True)),
        migrations.AddField(model_name='reservation', name='agreed_price',
            field=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)),
    ]
