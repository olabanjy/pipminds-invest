# Generated by Django 3.1.2 on 2021-01-02 00:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0013_auto_20201221_0212'),
    ]

    operations = [
        migrations.AddField(
            model_name='deposit',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('cancelled', 'Cancelled')], default='pending', max_length=200),
        ),
        migrations.AddField(
            model_name='withdrawal',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('cancelled', 'Cancelled')], default='pending', max_length=200),
        ),
    ]
