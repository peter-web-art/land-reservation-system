from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0005_user_kyc')]
    operations = [
        migrations.AddField(model_name='user', name='govt_letter',
            field=models.FileField(upload_to='kyc/govt_letters/', blank=True, null=True)),
        migrations.AddField(model_name='user', name='govt_letter_date',
            field=models.DateField(null=True, blank=True)),
    ]
