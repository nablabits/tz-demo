# Generated by Django 2.0.2 on 2019-01-19 07:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0071_auto_20190118_0959'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='in_b',
            field=models.BooleanField(default=False, verbose_name='En B'),
        ),
    ]
