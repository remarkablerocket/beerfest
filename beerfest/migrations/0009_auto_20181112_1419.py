# Generated by Django 2.1.2 on 2018-11-12 20:19

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('beerfest', '0008_remove_starbeer_starred'),
    ]

    operations = [
        migrations.CreateModel(
            name='BeerRating',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('beer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='beer_rating', to='beerfest.Beer')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='beer_rating', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='beerrating',
            unique_together={('user', 'beer')},
        ),
    ]