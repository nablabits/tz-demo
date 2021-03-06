# Generated by Django 2.0.2 on 2018-09-19 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0031_customer_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='chest',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Pecho'),
        ),
        migrations.AlterField(
            model_name='order',
            name='hip',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Cadera'),
        ),
        migrations.AlterField(
            model_name='order',
            name='lenght',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Largo'),
        ),
        migrations.AlterField(
            model_name='order',
            name='waist',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Cintura'),
        ),
    ]
