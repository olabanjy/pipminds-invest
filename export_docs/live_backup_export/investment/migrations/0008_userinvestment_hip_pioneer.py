# Generated by Django 3.1.2 on 2021-02-02 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0007_auto_20210129_0831'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvestment',
            name='hip_pioneer',
            field=models.BooleanField(default=False),
        ),
    ]