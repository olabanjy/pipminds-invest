# Generated by Django 3.1.2 on 2021-05-04 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0027_delete_poolswallet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deposit',
            name='wallet',
            field=models.CharField(choices=[('main', 'Main Wallet'), ('referrals', 'Referral Wallet'), ('investments', 'Investment Wallet')], default='main', max_length=200),
        ),
        migrations.AlterField(
            model_name='withdrawal',
            name='wallet',
            field=models.CharField(choices=[('main', 'Main Wallet'), ('referrals', 'Referral Wallet'), ('investments', 'Investment Wallet')], default='main', max_length=200),
        ),
    ]
