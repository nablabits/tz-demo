# Generated by Django 2.0.2 on 2018-11-07 16:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0043_auto_20181030_2138'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderitem',
            name='element',
        ),
    ]
