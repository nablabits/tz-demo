# Generated by Django 2.0.2 on 2018-09-14 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0027_auto_20180914_2030'),
    ]

    operations = [
        migrations.AddField(
            model_name='timing',
            name='activity',
            field=models.CharField(choices=[('1', 'Confección'), ('2', 'Corte'), ('3', 'Planchado')], default='1', max_length=1, verbose_name='Actividad'),
        ),
        migrations.AlterField(
            model_name='timing',
            name='item_class',
            field=models.CharField(choices=[('1', 'Standard'), ('2', 'Medium'), ('3', 'Premium')], default='1', max_length=1, verbose_name='Tipo Item'),
        ),
    ]