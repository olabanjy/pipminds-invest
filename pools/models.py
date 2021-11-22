from django.db import models
from django.conf import settings
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta, date, datetime
from django.utils import timezone
import uuid
from PIL import Image
from allauth.account.signals import user_signed_up, user_logged_in
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from users.models import * 
import random, string, os



class PoolPeriod(models.Model):
    name = models.CharField(max_length=200)
    maturity_desc = models.CharField(max_length=200)
    period_hrs = models.IntegerField()
    period_days = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - {self.period_hrs}"

class PoolOfferings(models.Model):
    name = models.CharField(max_length=200)
    desc = models.CharField(max_length=200, blank=True, null=True)
    price = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class PoolType(models.Model):
    name = models.CharField(max_length=200)
    unique_pool_type_id = models.CharField(max_length=200, default=f"PPT-{str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 8)))}")
    entry_window = models.ForeignKey(PoolPeriod, on_delete=models.DO_NOTHING, related_name="pool_period_entry_window", blank=True, null=True)
    active_period_window = models.ForeignKey(PoolPeriod, on_delete=models.DO_NOTHING, related_name="pool_period_active_window", blank=True, null=True)
    min_percentage_promise = models.IntegerField(default=1)
    max_percentage_promise = models.IntegerField(default=1)
    amount_per_slot = models.DecimalField(max_digits=19, decimal_places=2)
    can_spin_new = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)


    
    def __str__(self):
        return self.name



POOL_STATUS = (
    ("pending", "Pending"),
    ("running", "Running"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled")
)

class PoolInstance(models.Model):
    unique_instance_id = models.CharField(max_length=200, default=f"PPI-{str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 16)))}")
    pool_type = models.ForeignKey(PoolType, on_delete=models.CASCADE)
    status = models.CharField(max_length=200, choices=POOL_STATUS, default="pending")
    slots = models.IntegerField(default=0)
    value_bought = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    percentage_perf = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    all_earnings = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    entry_starts = models.DateField(max_length=100, blank=True, null=True)
    entry_ends = models.DateField(max_length=100, blank=True, null=True)
    run_starts = models.DateField(max_length=100, blank=True, null=True)
    run_ends = models.DateField(max_length=100, blank=True, null=True)
    active = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.unique_instance_id

    @property
    def get_days_left(self, *args, **kwargs):
        if self.status == "pending":
            if self.entry_ends >= datetime.astimezone(datetime.today()).date():
                return (self.entry_ends - datetime.astimezone(datetime.today()).date()).days
            else:
                return 0
        else:
            return 0
    @property
    def get_percentage_days_left(self, *args, **kwargs):
        if self.status == "pending":
            if self.entry_starts <= datetime.astimezone(datetime.today()).date():
                days_taken = (datetime.astimezone(datetime.today()).date() - self.entry_starts ).days
                print(days_taken)
                return (days_taken/self.pool_type.entry_window.period_days) * 100 
            else:
                return 0
        else:
            return 0
    
    @property
    def get_percentage_run_days_left(self, *args, **kwargs):
        if self.status == "running":
            if self.run_starts <= datetime.astimezone(datetime.today()).date():
                run_days_taken = (datetime.astimezone(datetime.today()).date() - self.run_starts ).days
                print(run_days_taken)
                return (run_days_taken/self.pool_type.active_period_window.period_days) * 100 
            else:
                return 0
        else:
            return 0
            

    
        
        


class UserPoolSlots(models.Model):
    tnx_code = models.CharField(max_length=200, default=f"{str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 11)))}")
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_pool_slots")
    pool_instance = models.ForeignKey(PoolInstance, on_delete=models.CASCADE, related_name="user_pool_instance")
    slots_taken = models.IntegerField(default=1)
    slots_value = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    contract_file =  models.FileField(upload_to='pipminds/pools_contracts', blank=True, null=True)
    # offerings = models.ManyToManyField(PoolOfferings)

    def __str__(self):
        return self.tnx_code

    @property
    def get_net_profit_earn(self, *args, **kwargs):
        if self.pool_instance.status == "completed":

            net_earning = (int(self.pool_instance.percentage_perf) / 100) * int(self.slots_value)
            return int(net_earning)
        else:
            return 0 



class PoolsWallet(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    deposit = models.DecimalField(max_digits=19, decimal_places=2, default=0.00 )

    def __str__(self):
        return f"{self.user.first_name} - {self.deposit}"

class UserOfferingsPurchase(models.Model):
    txn_code = models.CharField(max_length=200, default=f"{str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 8)))}")
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    offerings = models.ManyToManyField(PoolOfferings,related_name="users_offering_purchases")
    total_amount = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.txn_code







 




    

 