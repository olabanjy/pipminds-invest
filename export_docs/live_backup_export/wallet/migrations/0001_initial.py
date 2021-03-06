# Generated by Django 3.1.2 on 2020-11-29 01:35

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Withdrawal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('txn_code', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('wallet', models.CharField(choices=[('main', 'Main Wallet'), ('referrals', 'Referral Wallet'), ('investments', 'Investment Wallet')], default='main', max_length=200)),
                ('approved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='UserReferralEarnings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('txn_code', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('txn_code', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('txn_method', models.CharField(choices=[('paystack', 'Paystack'), ('manual', 'Manual'), ('stripe', 'Stripe'), ('paypal', 'Paypal')], default='paystack', max_length=200)),
                ('txn_type', models.CharField(choices=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal')], default='deposit', max_length=200)),
                ('approved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='ReferralWallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=19)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='MainWallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deposit', models.DecimalField(decimal_places=2, default=0.0, max_digits=19)),
                ('available_balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=19)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='InvestmentWallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=19)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='Deposit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('txn_code', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('wallet', models.CharField(choices=[('main', 'Main Wallet'), ('referrals', 'Referral Wallet'), ('investments', 'Investment Wallet')], default='main', max_length=200)),
                ('approved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
    ]
