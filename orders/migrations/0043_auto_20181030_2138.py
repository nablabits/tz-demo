# Generated by Django 2.0.2 on 2018-10-30 20:38

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0042_auto_add_default_item'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='item',
            options={'ordering': ('name',)},
        ),
        migrations.AddField(
            model_name='orderitem',
            name='crop',
            field=models.DurationField(default=datetime.timedelta(0), verbose_name='Corte'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='element',
            field=models.ManyToManyField(default=1, to='orders.Item'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='iron',
            field=models.DurationField(default=datetime.timedelta(0), verbose_name='Planchado'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='sewing',
            field=models.DurationField(default=datetime.timedelta(0), verbose_name='Confeccion'),
        ),
    ]
