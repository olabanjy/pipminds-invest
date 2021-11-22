# Generated by Django 3.1.2 on 2021-05-04 19:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0025_auto_20210504_1927'),
        ('pools', '0006_remove_pooltype_max_slots'),
    ]

    operations = [
        migrations.CreateModel(
            name='PoolsWallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deposit', models.DecimalField(decimal_places=2, default=0.0, max_digits=19)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
    ]