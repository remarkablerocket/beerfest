# Generated by Django 2.1.2 on 2018-11-12 14:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('beerfest', '0006_auto_20181112_0749'),
    ]

    operations = [
        migrations.RenameModel('UserBeer', 'StarBeer'),
        migrations.AlterField(
            model_name='starbeer',
            name='beer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='starbeer', to='beerfest.Beer'),
        ),
        migrations.AlterField(
            model_name='starbeer',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='starbeer', to=settings.AUTH_USER_MODEL),
        ),
    ]
