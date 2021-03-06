# Generated by Django 2.0.2 on 2018-06-07 15:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0015_auto_20180607_1528'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item', models.CharField(choices=[('1', 'Falda'), ('2', 'Camisa'), ('3', 'Corpiño'), ('4', 'Pañuelo'), ('5', 'Delantal'), ('6', 'Chaqueta'), ('7', 'Chaleco')], default='1', max_length=1, verbose_name='Item')),
                ('size', models.CharField(choices=[('1', 'XS'), ('2', 'S'), ('3', 'M'), ('4', 'L'), ('5', 'XL'), ('6', 'XXL')], default='1', max_length=1, verbose_name='Talla')),
                ('qty', models.IntegerField(default=1, verbose_name='Cantidad')),
                ('reference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.Order')),
            ],
        ),
    ]
