# Generated by Django 3.1.2 on 2020-10-12 23:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_code', models.CharField(max_length=200)),
                ('phone', models.CharField(blank=True, max_length=40, null=True)),
                ('first_name', models.CharField(blank=True, max_length=200, null=True)),
                ('last_name', models.CharField(blank=True, max_length=200, null=True)),
                ('dob', models.DateField(blank=True, max_length=100, null=True)),
                ('address_1', models.CharField(blank=True, max_length=500, null=True)),
                ('address_2', models.CharField(blank=True, max_length=500, null=True)),
                ('city', models.CharField(blank=True, max_length=200, null=True)),
                ('state', models.CharField(blank=True, max_length=200, null=True)),
                ('nationality', models.CharField(blank=True, max_length=200, null=True)),
                ('zip_code', models.CharField(blank=True, max_length=200, null=True)),
                ('profile_set_up', models.BooleanField(default=False)),
                ('investement_verified', models.BooleanField(default=False)),
                ('academic_verified', models.BooleanField(default=False)),
                ('ppp_verfied', models.BooleanField(default=False)),
                ('photo', models.ImageField(blank=True, default='default_profile_pics.jpg', upload_to='pipminds/user_profile/')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Referral',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sponsor_id', models.CharField(max_length=200)),
                ('downline_id', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='UserDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doc_type', models.CharField(choices=[('passport', 'Passport'), ('national_id', 'National ID'), ('driving_license', 'Driving License'), ('voter_card', 'Voters Card')], default='passport', max_length=200)),
                ('doc_front', models.ImageField(blank=True, null=True, upload_to='pipminds/user_profile/documents/')),
                ('doc_back', models.ImageField(blank=True, null=True, upload_to='pipminds/user_profile/documents/')),
                ('approved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='UserBankAccount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bank_name', models.CharField(blank=True, max_length=200, null=True)),
                ('account_name', models.CharField(blank=True, max_length=200, null=True)),
                ('account_number', models.CharField(blank=True, max_length=20, null=True)),
                ('swift_code', models.CharField(blank=True, max_length=20, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
        migrations.CreateModel(
            name='NextOfKin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(blank=True, max_length=200, null=True)),
                ('email', models.CharField(blank=True, max_length=200, null=True)),
                ('phone', models.CharField(blank=True, max_length=200, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
    ]
