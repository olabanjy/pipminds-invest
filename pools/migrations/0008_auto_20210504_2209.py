# Generated by Django 3.1.2 on 2021-05-04 22:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pools', '0007_poolswallet'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pooltype',
            name='period',
        ),
        migrations.RemoveField(
            model_name='pooltype',
            name='value',
        ),
        migrations.AddField(
            model_name='poolinstance',
            name='entry_ends',
            field=models.DateField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='poolinstance',
            name='entry_starts',
            field=models.DateField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='poolinstance',
            name='run_ends',
            field=models.DateField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='poolinstance',
            name='run_starts',
            field=models.DateField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='poolinstance',
            name='value_bought',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True),
        ),
        migrations.AddField(
            model_name='poolofferings',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True),
        ),
        migrations.AddField(
            model_name='pooltype',
            name='active_period_window',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='pool_period_active_window', to='pools.poolperiod'),
        ),
        migrations.AddField(
            model_name='pooltype',
            name='approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pooltype',
            name='entry_window',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='pool_period_entry_window', to='pools.poolperiod'),
        ),
        migrations.AlterField(
            model_name='poolinstance',
            name='unique_instance_id',
            field=models.CharField(default='PPT-DLFPD815HIF', max_length=200),
        ),
        migrations.AlterField(
            model_name='pooltype',
            name='unique_pool_type_id',
            field=models.CharField(default='PPT-NQQ3UMKKBNW', max_length=200),
        ),
    ]
