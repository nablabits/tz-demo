# Generated by Django 2.0.2 on 2018-04-19 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_auto_20180330_1357'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='CIF',
            field=models.CharField(blank=True, max_length=10, verbose_name='CIF'),
        ),
    ]
