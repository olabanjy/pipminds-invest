# Generated by Django 3.1.2 on 2021-03-04 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0007_auto_20210209_2348'),
    ]

    operations = [
        migrations.AddField(
            model_name='deposit',
            name='proof_of_payment',
            field=models.FileField(blank=True, null=True, upload_to='deposit/proof_of_payment'),
        ),
        migrations.AlterField(
            model_name='deposit',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('cancelled', 'Cancelled'), ('awaiting_proof', 'Awaiting Proof')], default='pending', max_length=200),
        ),
        migrations.AlterField(
            model_name='payments',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('cancelled', 'Cancelled'), ('awaiting_proof', 'Awaiting Proof')], default='pending', max_length=200),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='txn_method',
            field=models.CharField(choices=[('paystack', 'Paystack'), ('manual', 'Manual'), ('stripe', 'Stripe'), ('paypal', 'Paypal'), ('monnify', 'Monnify')], default='paystack', max_length=200),
        ),
        migrations.AlterField(
            model_name='withdrawal',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('cancelled', 'Cancelled'), ('awaiting_proof', 'Awaiting Proof')], default='pending', max_length=200),
        ),
    ]
