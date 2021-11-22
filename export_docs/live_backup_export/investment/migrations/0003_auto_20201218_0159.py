# Generated by Django 3.1.2 on 2020-12-18 01:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0002_exchangerates'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='investmentplan',
            name='max_maturity_period',
        ),
        migrations.RemoveField(
            model_name='investmentplan',
            name='min_maturity_period',
        ),
        migrations.AddField(
            model_name='investmentplan',
            name='first_maturity_period',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentplan',
            name='fourth_maturity_period',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentplan',
            name='second_maturity_period',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='investmentplan',
            name='third_maturity_period',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
