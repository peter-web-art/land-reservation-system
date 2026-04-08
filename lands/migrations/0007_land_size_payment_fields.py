from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0006_reservation_customer_email_reservation_customer_name'),
    ]

    operations = [
        migrations.AddField(model_name='land', name='size',
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name='land', name='size_unit',
            field=models.CharField(max_length=10, default='acres', blank=True,
                choices=[('acres','Acres'),('hectares','Hectares'),('sqm','Sq. Metres')])),
        migrations.AddField(model_name='land', name='land_use',
            field=models.CharField(max_length=20, default='agricultural', blank=True,
                choices=[('agricultural','Agricultural'),('residential','Residential'),
                         ('commercial','Commercial'),('industrial','Industrial'),('mixed','Mixed Use')])),
        migrations.AddField(model_name='land', name='is_active',
            field=models.BooleanField(default=True)),
        migrations.AddField(model_name='land', name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True)),
        migrations.AddField(model_name='reservation', name='payment_status',
            field=models.CharField(max_length=20, default='unpaid',
                choices=[('unpaid','Unpaid'),('paid','Paid'),('refunded','Refunded')])),
        migrations.AddField(model_name='reservation', name='payment_method',
            field=models.CharField(max_length=20, blank=True, null=True,
                choices=[('mpesa','M-Pesa'),('airtel','Airtel Money'),('tigopesa','Tigo Pesa'),
                         ('bank','Bank Transfer'),('cash','Cash on Arrival')])),
        migrations.AddField(model_name='reservation', name='payment_reference',
            field=models.CharField(max_length=100, blank=True, null=True)),
        migrations.AddField(model_name='reservation', name='amount_paid',
            field=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name='reservation', name='notes',
            field=models.TextField(blank=True)),
    ]
