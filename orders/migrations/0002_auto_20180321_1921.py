# Generated by Django 2.0.2 on 2018-03-21 18:21

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='creation',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Alta'),
        ),
        migrations.AlterField(
            model_name='orders',
            name='inbox_date',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha de entrada'),
        ),
    ]