# Generated by Django 3.1.2 on 2021-03-03 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0018_auto_20210208_2007'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='txn_method',
            field=models.CharField(choices=[('paystack', 'Paystack'), ('manual', 'Manual'), ('stripe', 'Stripe'), ('paypal', 'Paypal'), ('monnify', 'Monnify')], default='paystack', max_length=200),
        ),
    ]