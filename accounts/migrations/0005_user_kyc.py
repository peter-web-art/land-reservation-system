from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0004_user_role_is_verified_is_suspended')]
    operations = [
        migrations.AddField(model_name='user', name='kyc_document',
            field=models.FileField(upload_to='kyc/', blank=True, null=True)),
        migrations.AddField(model_name='user', name='kyc_status',
            field=models.CharField(max_length=20, default='not_submitted',
                choices=[('not_submitted','Not Submitted'),('pending','Pending Review'),
                         ('approved','Approved'),('rejected','Rejected')])),
        migrations.AddField(model_name='user', name='kyc_notes',
            field=models.TextField(blank=True)),
    ]
