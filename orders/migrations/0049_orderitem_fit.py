# Generated by Django 2.0.2 on 2018-11-24 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0048_auto_20181116_1851'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='fit',
            field=models.BooleanField(default=False, verbose_name='Arreglo'),
        ),
    ]
