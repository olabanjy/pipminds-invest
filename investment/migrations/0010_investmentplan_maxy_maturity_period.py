# Generated by Django 3.1.2 on 2020-12-17 23:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0009_exchangerates'),
    ]

    operations = [
        migrations.AddField(
            model_name='investmentplan',
            name='maxy_maturity_period',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
