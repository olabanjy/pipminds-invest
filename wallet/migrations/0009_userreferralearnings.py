# Generated by Django 3.1.2 on 2020-10-29 14:14

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20201028_1614'),
        ('wallet', '0008_auto_20201029_1423'),
    ]

    operations = [
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
    ]
