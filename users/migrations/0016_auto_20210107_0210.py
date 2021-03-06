# Generated by Django 3.1.2 on 2021-01-07 01:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_userimportdoc'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='pioneer_ppp_member',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='userimportdoc',
            name='doc',
            field=models.FileField(blank=True, null=True, upload_to='pipminds/import_documents/admin_import'),
        ),
    ]
