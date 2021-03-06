# Generated by Django 2.0.2 on 2019-01-03 08:27

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0059_invoice'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankMovement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_date', models.DateField(default=django.utils.timezone.now, verbose_name='Fecha del moviento')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=7, verbose_name='Cantidad')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Observaciones')),
            ],
            options={
                'ordering': ['-action_date'],
            },
        ),
        migrations.AlterModelOptions(
            name='invoice',
            options={'ordering': ['-invoice_no']},
        ),
    ]
