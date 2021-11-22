# Generated by Django 3.1.2 on 2020-10-28 15:14

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20201028_1137'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserReferrals',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('downline', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='downline', to='users.profile')),
                ('sponsor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sponsor', to='users.profile')),
            ],
        ),
    ]