# Generated by Django 2.0.2 on 2018-12-13 19:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0052_auto_20181207_1641'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='stock',
            field=models.BooleanField(default=False, verbose_name='Stock'),
        ),
    ]