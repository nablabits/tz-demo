# Generated by Django 2.0.2 on 2018-12-15 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0054_pqueue'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pqueue',
            name='score',
            field=models.IntegerField(blank=True, unique=True),
        ),
    ]
