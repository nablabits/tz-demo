# Generated by Django 2.0.2 on 2018-06-08 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0016_orderitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='item',
            field=models.CharField(choices=[('1', 'Falda'), ('2', 'Pantalón'), ('3', 'Camisa'), ('4', 'Pañuelo'), ('5', 'Delantal'), ('6', 'Corpiño'), ('7', 'Chaleco')], default='1', max_length=1, verbose_name='Item'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='size',
            field=models.CharField(default='1', max_length=1, verbose_name='Talla'),
        ),
    ]
