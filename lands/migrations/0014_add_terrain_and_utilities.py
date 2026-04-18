from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0013_reservation_lands_reser_land_id_c0ff64_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='land',
            name='topography',
            field=models.CharField(blank=True, choices=[('flat', 'Flat'), ('sloped', 'Sloped'), ('rolling', 'Rolling Hills'), ('mountainous', 'Mountainous'), ('depressed', 'Depressed/Lowland')], default='flat', max_length=20),
        ),
        migrations.AddField(
            model_name='land',
            name='has_water',
            field=models.BooleanField(default=False, help_text='Access to water (well/tap/river)'),
        ),
        migrations.AddField(
            model_name='land',
            name='has_electricity',
            field=models.BooleanField(default=False, help_text='Access to power grid'),
        ),
        migrations.AddField(
            model_name='land',
            name='road_access',
            field=models.BooleanField(default=True, help_text='Accessible by vehicle/road'),
        ),
        migrations.AddField(
            model_name='land',
            name='is_fenced',
            field=models.BooleanField(default=False, help_text='Is the land fenced?'),
        ),
        migrations.AddField(
            model_name='land',
            name='is_cleared',
            field=models.BooleanField(default=False, help_text='Is the land cleared of bushes/trees?'),
        ),
    ]
