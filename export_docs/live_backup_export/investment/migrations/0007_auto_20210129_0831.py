# Generated by Django 3.1.2 on 2021-01-29 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0006_userinvestment_cip_pioneer'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvestment',
            name='mig_batch',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='userinvestment',
            name='mig_modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
