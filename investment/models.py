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



class InvestmentPeriod(models.Model):
    name = models.CharField(max_length=200)
    maturity_desc = models.CharField(max_length=200)
    period_hrs = models.IntegerField()
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name



class InvestmentCategory(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name



class InvestmentPlan(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(InvestmentCategory, on_delete=models.CASCADE)
    percentage_interest = models.IntegerField()
    min_investment = models.DecimalField(max_digits=19, decimal_places=2)
    max_investment = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
    first_maturity_period= models.IntegerField(blank=True, null=True)
    second_maturity_period= models.IntegerField(blank=True, null=True)
    third_maturity_period=models.IntegerField(blank=True, null=True)
    fourth_maturity_period=models.IntegerField(blank=True, null=True)
    period = models.ForeignKey(InvestmentPeriod, on_delete=models.DO_NOTHING)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

 
class UserInvestment(models.Model):
    display_name = models.CharField(max_length=200, blank=True, null=True)
    txn_code = models.CharField(max_length=200)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_investments")
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    plan = models.ForeignKey(InvestmentPlan, on_delete=models.CASCADE)
    maturity_days = models.IntegerField(blank=True, null=True)
    profit_earned = models.IntegerField(default=0)
    profit_paid = models.IntegerField(default=0)
    maturity_date = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    has_been_rolled_over = models.BooleanField(default=False)
    is_rollover = models.BooleanField(default=False)
    can_top_up = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    next_payout = models.DateTimeField(blank=True, null=True)
    cip_pioneer = models.BooleanField(default=False)
    hip_pioneer = models.BooleanField(default=False)
    mig_batch = models.CharField(max_length=200, blank=True, null=True)
    mig_modified = models.DateTimeField(auto_now=True)
    contract_file =  models.FileField(upload_to='pipminds/investment_contracts', blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.amount} - {self.txn_code}"


    @property
    def get_last_payout(self, *args, **kwargs):
        if self.plan.category.name == "CIP":
            if self.next_payout and datetime.astimezone(datetime.today()) > (self.created_at + timedelta(days=31)):  
                last_payout = (self.next_payout - timedelta(days=30)).date()
                return last_payout
            else:
                last_payout = self.created_at.date()
                return last_payout
            return None
        elif self.plan.category.name == "HIP":
            return self.created_at.date() 

    
    @property
    def get_topup_starts(self, *args, **kwargs):
        if self.plan.category.name == "CIP":
            if self.next_payout and datetime.astimezone(datetime.today()) > (self.created_at + timedelta(days=31)):  
                last_payout = self.next_payout - timedelta(days=30)
                return (last_payout + timedelta(minutes=1)).date()
            else:
                return None
        elif self.plan.category.name == "HIP":
            return (self.created_at + timedelta(minutes=1)).date()

       

    @property
    def get_topup_ends(self, *args, **kwargs):
        if self.plan.category.name == "CIP":
            if self.next_payout and datetime.astimezone(datetime.today()) > (self.created_at + timedelta(days=31)):  
                last_payout = self.next_payout - timedelta(days=30)
                return (last_payout + timedelta(days=8)).date()
            else:
                return None
        elif self.plan.category.name == "HIP":
            return (self.created_at + timedelta(days=14)).date()
    


    @property
    def get_future_topup_starts(self, *args, **kwargs):
        if self.plan.category.name == "CIP":
            return (self.next_payout + timedelta(minutes=1)).date()
        elif self.plan.category.name == "HIP":
            return (self.created_at + timedelta(minutes=1)).date()


    @property
    def get_future_topup_ends(self, *args, **kwargs):
        if self.plan.category.name == "CIP":
            return (self.next_payout + timedelta(days=8)).date()  
        elif self.plan.category.name == "HIP":
            return (self.created_at + timedelta(days=14)).date()

    @property
    def get_rollover_starts(self, *args, **kwargs):
        if self.completed:
            return (self.maturity_date + timedelta(minutes=1)).date()
        return None 
    
    @property
    def get_rollover_ends(self, *args, **kwargs):
        if self.completed:
            return (self.maturity_date + timedelta(days=7)).date()
        return None 

    @property
    def top_up_eligible(self, *args, **kwargs):
        if self.can_top_up:
            print("user can topup")
            if self.plan.category.name == "CIP":
                top_ups = UserInvestmentTopups.objects.filter(investment=self, user=self.user)
                if top_ups.exists():
                    print("User has done topup before ")
                    top_up_count = top_ups.count()
                    if self.maturity_days == 180:
                        return False
                    elif self.maturity_days == 270:
                        return False
                    elif self.maturity_days == 365 and top_up_count >= 2:
                        return False 
                else:
                    print("User has not done topup before ")
                    return True  
            else:
                return True 
        else:
            return False 


class UserInvestmentTopups(models.Model):
    investment = models.ForeignKey(UserInvestment, on_delete=models.CASCADE, related_name="user_investment_topup", blank=True, null=True)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    contract_file =  models.FileField(upload_to='pipminds/investment_top_up_contracts', blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.amount}" 

class UserInvestmentRollovers(models.Model):
    old_investment = models.ForeignKey(UserInvestment, on_delete=models.CASCADE, related_name="user_investment_rollover_old", blank=True, null=True)
    new_investment = models.ForeignKey(UserInvestment, on_delete=models.CASCADE, related_name="user_investment_rollover_new", blank=True, null=True)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.first_name}"        


class UserInvestmentEarnings(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    plan = models.ForeignKey(UserInvestment, on_delete=models.CASCADE, related_name="user_investment_earnings", blank=True, null=True)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    active = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.first_name} - {self.amount}"


class ExchangeRates(models.Model):
    name = models.CharField(max_length=200)
    rate_to_base = models.IntegerField()

    def __str__(self):
        return self.name

class CapitalPaybacks(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    investment = models.ForeignKey(UserInvestment, on_delete=models.CASCADE, related_name="user_investment_capital_payback", blank=True, null=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.user.email} -{self.investment.txn_code}"



    

 