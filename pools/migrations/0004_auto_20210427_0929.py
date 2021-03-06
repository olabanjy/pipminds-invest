# Generated by Django 3.1.2 on 2021-04-27 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pools', '0003_auto_20210425_1019'),
    ]

    operations = [
        migrations.AddField(
            model_name='pooltype',
            name='max_percentage_promise',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='pooltype',
            name='min_percentage_promise',
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='poolinstance',
            name='slots',
            field=models.IntegerField(default=0),
        ),
    ]
