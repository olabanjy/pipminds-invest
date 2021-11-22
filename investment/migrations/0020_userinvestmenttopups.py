# Generated by Django 3.1.2 on 2021-02-22 14:10

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_auto_20210124_2114'),
        ('investment', '0019_userinvestment_hip_pioneer'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserInvestmentTopups',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('investment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_investment_topup', to='investment.userinvestment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
    ]