# Generated by Django 2.0.2 on 2018-12-27 17:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0057_auto_20181225_2105'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=6, verbose_name='Precio unitario'),
            preserve_default=False,
        ),
    ]