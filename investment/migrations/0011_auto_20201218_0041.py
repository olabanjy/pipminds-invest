# Generated by Django 3.1.2 on 2020-12-17 23:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0010_investmentplan_maxy_maturity_period'),
    ]

    operations = [
        migrations.RenameField(
            model_name='investmentplan',
            old_name='maxy_maturity_period',
            new_name='first_maturity_period',
        ),
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
            name='thrid_maturity_period',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
