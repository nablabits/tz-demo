# Generated by Django 2.0.2 on 2018-09-21 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0034_auto_20180921_1353'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='item',
            field=models.CharField(choices=[('1', 'Falda'), ('2', 'Pantalón'), ('3', 'Camisa'), ('4', 'Pañuelo'), ('5', 'Delantal'), ('6', 'Corpiño'), ('7', 'Chaleco'), ('8', 'Gerriko'), ('9', 'Bata'), ('10', 'Pololo'), ('11', 'Azpikogona'), ('12', 'Traje de niña')], default='1', max_length=1, verbose_name='Item'),
        ),
        migrations.AlterField(
            model_name='timing',
            name='item',
            field=models.CharField(choices=[('1', 'Falda'), ('2', 'Pantalón'), ('3', 'Camisa'), ('4', 'Pañuelo'), ('5', 'Delantal'), ('6', 'Corpiño'), ('7', 'Chaleco'), ('8', 'Gerriko'), ('9', 'Bata'), ('10', 'Pololo'), ('11', 'Azpikogona'), ('12', 'Traje de niña')], default='1', max_length=1, verbose_name='Item'),
        ),
    ]
