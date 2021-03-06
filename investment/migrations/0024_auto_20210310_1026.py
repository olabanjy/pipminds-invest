# Generated by Django 3.1.2 on 2021-03-10 10:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0023_auto_20210310_0837'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvestmentrollovers',
            name='new_investment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_investment_rollover_new', to='investment.userinvestment'),
        ),
        migrations.AlterField(
            model_name='userinvestmentrollovers',
            name='old_investment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_investment_rollover_old', to='investment.userinvestment'),
        ),
    ]
