# Generated by Django 2.0.2 on 2018-08-29 09:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0023_remove_customer_notif'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='comment',
            field=models.TextField(verbose_name='Comentario'),
        ),
    ]
