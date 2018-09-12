# Generated by Django 2.0.2 on 2018-09-12 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0024_auto_20180829_1157'),
    ]

    operations = [
        migrations.CreateModel(
            name='Timing',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item', models.CharField(choices=[('1', 'Falda'), ('2', 'Pantalón'), ('3', 'Camisa'), ('4', 'Pañuelo'), ('5', 'Delantal'), ('6', 'Corpiño'), ('7', 'Chaleco'), ('8', 'Gerriko')], default='1', max_length=1, verbose_name='Item')),
                ('qty', models.IntegerField(default=1, verbose_name='Cantidad')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Observaciones')),
                ('time', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Tiempo (h)')),
            ],
        ),
    ]
