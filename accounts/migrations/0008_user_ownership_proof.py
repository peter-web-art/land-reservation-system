from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_user_kyc_document_alter_user_kyc_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='ownership_proof',
            field=models.FileField(
                blank=True,
                help_text='Separate land title or ownership proof document',
                null=True,
                upload_to='kyc/ownership/',
            ),
        ),
    ]
