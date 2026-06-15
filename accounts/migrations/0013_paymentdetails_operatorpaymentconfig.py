# Generated migration for PaymentDetails and OperatorPaymentConfig models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_systemsettings_platform_fee_percentage'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('payment_method', models.CharField(choices=[('mpesa', 'M-Pesa'), ('airtel', 'Airtel Money'), ('tigo', 'Tigo Money'), ('bank_transfer', 'Bank Transfer'), ('bank_cheque', 'Bank Cheque')], default='mpesa', help_text='Preferred payment method for receiving payouts', max_length=20)),
                ('account_identifier', models.CharField(blank=True, help_text='M-Pesa number, bank account number, etc.', max_length=100)),
                ('account_holder_name', models.CharField(blank=True, help_text='Name associated with the payment account', max_length=200)),
                ('bank_name', models.CharField(blank=True, help_text='Bank name (if applicable)', max_length=100)),
                ('bank_branch', models.CharField(blank=True, help_text='Bank branch (if applicable)', max_length=100)),
                ('is_verified', models.BooleanField(default=False, help_text='Admin has verified these payment details')),
                ('verified_on', models.DateTimeField(blank=True, null=True)),
                ('is_default', models.BooleanField(default=True, help_text='Use as default for payouts')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paymentdetails_created', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paymentdetails_updated', to=settings.AUTH_USER_MODEL)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment_details', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Payment Details',
            },
        ),
        migrations.CreateModel(
            name='OperatorPaymentConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('payment_method', models.CharField(choices=[('mpesa', 'M-Pesa'), ('airtel', 'Airtel Money'), ('tigo', 'Tigo Money'), ('bank_transfer', 'Bank Transfer'), ('bank_cheque', 'Bank Cheque')], help_text='Payment method customers should use', max_length=20, unique=True)),
                ('account_identifier', models.CharField(help_text='M-Pesa number, bank account, etc. where customers pay', max_length=100)),
                ('account_holder_name', models.CharField(help_text='Business/operator name', max_length=200)),
                ('bank_name', models.CharField(blank=True, help_text='Bank name (if applicable)', max_length=100)),
                ('bank_branch', models.CharField(blank=True, help_text='Bank branch (if applicable)', max_length=100)),
                ('instructions', models.TextField(blank=True, help_text='Payment instructions to display to customers')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this payment method is available')),
                ('priority', models.PositiveIntegerField(default=0, help_text='Display order (0 = highest priority)')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operatorpaymentconfig_created', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operatorpaymentconfig_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Operator Payment Config',
                'ordering': ['priority', '-created_on'],
            },
        ),
    ]
