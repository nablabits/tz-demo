# Generated by Django 2.0.2 on 2018-03-21 18:17

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.timezone import utc


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comments',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation', models.DateTimeField(default=datetime.datetime(2018, 3, 21, 18, 17, 4, 669203, tzinfo=utc), verbose_name='Alta')),
                ('name', models.CharField(max_length=64, verbose_name='Nombre')),
                ('address', models.CharField(blank=True, max_length=64, verbose_name='Dirección')),
                ('city', models.CharField(max_length=32, verbose_name='Localidad')),
                ('phone', models.IntegerField(verbose_name='Telefonoa')),
                ('email', models.EmailField(blank=True, max_length=64, verbose_name='Eposta')),
                ('CIF', models.CharField(max_length=10, verbose_name='CIF')),
                ('cp', models.IntegerField(verbose_name='CP')),
                ('notif', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Orders',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inbox_date', models.DateTimeField(default=datetime.datetime(2018, 3, 21, 18, 17, 4, 670103, tzinfo=utc), verbose_name='Fecha de entrada')),
                ('delivery', models.DateField()),
                ('status', models.CharField(choices=[('1', 'Inboxed'), ('2', 'Waiting'), ('3', 'preparing'), ('4', 'performing'), ('5', 'WorkShop'), ('6', 'Outbox'), ('7', 'Delivered')], max_length=1)),
                ('waist', models.DecimalField(decimal_places=2, max_digits=3)),
                ('chest', models.DecimalField(decimal_places=2, max_digits=3)),
                ('hip', models.DecimalField(decimal_places=2, max_digits=3)),
                ('lenght', models.DecimalField(decimal_places=2, max_digits=3)),
                ('others', models.TextField(blank=True)),
                ('budget', models.DecimalField(decimal_places=2, max_digits=5)),
                ('prepaid', models.DecimalField(decimal_places=2, max_digits=5)),
                ('workshop', models.DecimalField(decimal_places=2, max_digits=3)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
