# Generated by Django 3.1.2 on 2021-04-04 03:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_auto_20210404_0312'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptioninstance',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='profile_subscription_instance', to='users.profile'),
        ),
    ]