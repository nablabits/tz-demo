# Generated by Django 2.0.2 on 2018-07-04 10:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0022_orderitem_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='notif',
        ),
    ]