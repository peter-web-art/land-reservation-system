# Generated migration for LandReport model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0015_utility_rename_image_land_land_image_path_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LandReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('reason', models.CharField(choices=[('spam', 'Spam or Misleading'), ('fake', 'Fake or Fraudulent'), ('illegal', 'Illegal Activity'), ('harassment', 'Harassment or Abuse'), ('scam', 'Suspected Scam'), ('inappropriate', 'Inappropriate Content'), ('duplicate', 'Duplicate Listing'), ('other', 'Other')], max_length=50)),
                ('description', models.TextField(help_text='Detailed explanation of the report')),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('reviewed', 'Under Review'), ('resolved', 'Resolved'), ('dismissed', 'Dismissed')], default='submitted', max_length=20)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin notes on investigation or action taken')),
                ('reviewed_on', models.DateTimeField(blank=True, null=True)),
                ('is_spam', models.BooleanField(default=False, help_text='Mark as spam report itself')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='landreport_created', to=settings.AUTH_USER_MODEL)),
                ('land', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='lands.land')),
                ('reported_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='land_reports', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='land_reports_reviewed', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='landreport_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Land Report',
                'verbose_name_plural': 'Land Reports',
                'ordering': ['-created_on'],
            },
        ),
        migrations.AddConstraint(
            model_name='landreport',
            constraint=models.UniqueConstraint(fields=('land', 'reported_by'), name='unique_land_report_per_user'),
        ),
    ]
