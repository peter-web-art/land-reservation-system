# Generated manually for LandImage model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0010_land_latitude_land_longitude_land_view_count_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LandImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='lands/gallery/')),
                ('caption', models.CharField(blank=True, help_text='Optional caption', max_length=200)),
                ('is_primary', models.BooleanField(default=False, help_text='Set as primary/cover image')),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('land', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='lands.land')),
            ],
            options={
                'ordering': ['order', '-is_primary', 'created_at'],
            },
        ),
    ]
