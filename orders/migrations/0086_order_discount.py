# Generated by Django 2.2 on 2019-12-26 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0085_orderitem_batch'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='discount',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Descuento %'),
        ),
    ]
