# Generated by Django 2.0.2 on 2018-09-17 11:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0029_timing_reference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timing',
            name='reference',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='orders.Order'),
        ),
    ]
