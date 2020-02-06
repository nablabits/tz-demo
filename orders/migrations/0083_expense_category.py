# Generated by Django 2.2 on 2019-12-21 13:19

from django.db import migrations, models
import django.db.models.deletion
import orders.models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0082_expensecategory'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='category',
            field=models.ForeignKey(default=orders.models.default_category, on_delete=django.db.models.deletion.SET_DEFAULT, to='orders.ExpenseCategory'),
        ),
    ]