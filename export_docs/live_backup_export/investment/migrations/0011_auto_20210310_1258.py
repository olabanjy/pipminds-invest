# Generated by Django 3.1.2 on 2021-03-10 12:58

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20210124_2119'),
        ('investment', '0010_auto_20210227_1627'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvestment',
            name='has_been_rolled_over',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userinvestment',
            name='is_rollover',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='UserInvestmentRollovers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('new_investment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_investment_rollover_new', to='investment.userinvestment')),
                ('old_investment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_investment_rollover_old', to='investment.userinvestment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.profile')),
            ],
        ),
    ]
