# Generated by Django 3.1.2 on 2021-04-06 05:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0027_remove_userinvestment_terminated'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvestment',
            name='can_top_up',
            field=models.BooleanField(default=False),
        ),
    ]
