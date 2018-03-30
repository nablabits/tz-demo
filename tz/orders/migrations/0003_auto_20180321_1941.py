# Generated by Django 2.0.2 on 2018-03-21 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_auto_20180321_1921'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='CIF',
            field=models.CharField(blank=True, max_length=10, verbose_name='CIF'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='phone',
            field=models.IntegerField(verbose_name='Telefono'),
        ),
        migrations.AlterField(
            model_name='orders',
            name='budget',
            field=models.DecimalField(decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='orders',
            name='chest',
            field=models.DecimalField(decimal_places=2, max_digits=5),
        ),
        migrations.AlterField(
            model_name='orders',
            name='delivery',
            field=models.DateField(blank=True),
        ),
        migrations.AlterField(
            model_name='orders',
            name='hip',
            field=models.DecimalField(decimal_places=2, max_digits=5),
        ),
        migrations.AlterField(
            model_name='orders',
            name='lenght',
            field=models.DecimalField(decimal_places=2, max_digits=5),
        ),
        migrations.AlterField(
            model_name='orders',
            name='prepaid',
            field=models.DecimalField(decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='orders',
            name='waist',
            field=models.DecimalField(decimal_places=2, max_digits=5),
        ),
        migrations.AlterField(
            model_name='orders',
            name='workshop',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, verbose_name='Horas de taller'),
        ),
    ]