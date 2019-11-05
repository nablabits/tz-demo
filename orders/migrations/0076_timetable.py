# Generated by Django 2.2 on 2019-05-16 13:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0075_order_confirmed'),
    ]

    operations = [
        migrations.CreateModel(
            name='Timetable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(default=django.utils.timezone.now, verbose_name='entrada')),
                ('end', models.DateTimeField(blank=True, null=True, verbose_name='salida')),
                ('hours', models.DurationField(blank=True, null=True, verbose_name='horas')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]