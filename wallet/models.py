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
from decimal import Decimal

class MainWallet(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    deposit = models.DecimalField(max_digits=19, decimal_places=2, default=0.00 )
    available_balance = models.DecimalField(max_digits=19, decimal_places=2, default=0.00 )

    @property
    def overall_balance(self):
        if self.deposit and self.available_balance != None or 0.00:
            return self.deposit + self.available_balance
        return 0.00


    def __str__(self):
        return f"{self.user.first_name} - {self.overall_balance}"


class InvestmentWallet(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    balance = models.DecimalField(max_digits=19, decimal_places=2,  default=0.00 )

    def __str__(self):
        return f"{self.user.first_name} - {self.balance}"
    


class ReferralWallet(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    balance = models.DecimalField(max_digits=19, decimal_places=2, default=0.00 )

    def __str__(self):
        return f"{self.user.first_name} - {self.balance}"


TXN_METHOD = (
    ("paystack", "Paystack"),
    ("manual", "Manual"),
    ("stripe", "Stripe"),
    ("paypal", "Paypal"),
    ("monnify", "Monnify")
)

TXN_TYPE = (
    ("deposit", "Deposit"),
    ("withdrawal", "Withdrawal"),
    ("investment_earnings", "Investment Earnings"),
    ("referral_earnings", "Referral Earnings")

)


class Transaction(models.Model):
    txn_code = models.CharField(max_length=200)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    txn_method = models.CharField(max_length=200, choices=TXN_METHOD, default="paystack")
    txn_type = models.CharField(max_length=200, choices=TXN_TYPE, default="deposit")
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    trans_ref = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.txn_code


    @property
    def get_timeout_time(self, *args, **kwargs):
        if self.txn_method == "manual":
            timeout = self.created_at + timedelta(hours=48)
            return timeout
        return None



WHICH_WALLET = (
    ("main", "Main Wallet"),
    ("referrals", "Referral Wallet"),
    ("investments", "Investment Wallet")
)


STATUS_TYPE = (
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("cancelled", "Cancelled"),
    ("awaiting_proof", "Awaiting Proof")

)

class Withdrawal(models.Model):
    txn_code = models.CharField(max_length=200)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    wallet = models.CharField(max_length=200, choices=WHICH_WALLET, default="main")
    status = models.CharField(max_length=200, choices=STATUS_TYPE, default="pending")
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    trans_ref = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.txn_code

class Deposit(models.Model):
    txn_code = models.CharField(max_length=200)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    wallet = models.CharField(max_length=200, choices=WHICH_WALLET, default="main")
    status = models.CharField(max_length=200, choices=STATUS_TYPE, default="pending")
    approved = models.BooleanField(default=False)
    proof_of_payment = models.FileField(upload_to='deposit/proof_of_payment', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    trans_ref = models.CharField(max_length=200, blank=True, null=True)
    

    def __str__(self):
        return self.txn_code

    


class UserReferralEarnings(models.Model):
    txn_code = models.CharField(max_length=200)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.txn_code} - {self.amount}"


PAYMENT_DESTINATION = (
    ("investment_wallet", "Investment Wallet"),
    ("referral_wallet", "Referral Wallet"),
    ("bank_account", "Bank Account")
)

class Payments(models.Model):
    txn_code = models.CharField(max_length=200)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    status = models.CharField(max_length=200, choices=STATUS_TYPE, default="pending")
    destination = models.CharField(max_length=200, choices=PAYMENT_DESTINATION, default="bank_account")
    approved = models.BooleanField(default=False)
    remark = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    modified_at = models.DateTimeField(auto_now=True)
    trans_ref = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.user.email} - {self.amount}"



class WebhookBackup(models.Model):
    pay_sol = models.CharField(max_length=500, blank=True, null=True)
    the_trans = models.ForeignKey(Transaction, on_delete=models.CASCADE, blank=True, null=True)
    req_body = models.TextField(blank=True, null=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.pay_sol




