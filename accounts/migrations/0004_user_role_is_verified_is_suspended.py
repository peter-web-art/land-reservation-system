from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_is_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('customer', 'Customer'), ('owner', 'Land Owner'), ('admin', 'Admin')],
                default='customer',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='is_verified',
            field=models.BooleanField(
                default=False,
                help_text='Owner verified by admin — no scam risk',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='is_suspended',
            field=models.BooleanField(
                default=False,
                help_text='Suspended users cannot log in',
            ),
        ),
    ]
