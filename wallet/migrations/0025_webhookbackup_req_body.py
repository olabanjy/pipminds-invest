# Generated by Django 3.1.2 on 2021-04-08 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0024_webhookbackup_approved'),
    ]

    operations = [
        migrations.AddField(
            model_name='webhookbackup',
            name='req_body',
            field=models.TextField(blank=True, null=True),
        ),
    ]
