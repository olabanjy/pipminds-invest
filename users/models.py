from django.db import models
from django.conf import settings
from django.urls import reverse
from django.db.models.signals import post_save, post_init, pre_save
from django.dispatch import receiver
from datetime import datetime
from django.utils import timezone
from django.db.models import Sum
import uuid
from PIL import Image
from allauth.account.signals import user_signed_up, user_logged_in
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import random, string
from .tasks import *
from datetime import timedelta, date, datetime
from paystackapi.paystack import Paystack
paystack_secret_key = settings.PAYSTACK_SECRET_KEY

paystack = Paystack(secret_key=paystack_secret_key)



STATUS_TYPE = (
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected")
)


TEST_PHASE = (
    ("live_prod", "Live Prod"),
    ("phase_one", "Phase One"),
    ("phase_two", "Phase Two"),
    ("beta", "Beta")
)

 
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_code = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, null=True, blank=True,)
    first_name = models.CharField(blank=True, null=True, max_length=200)
    last_name = models.CharField(blank=True, null=True, max_length=200)
    dob = models.DateField(max_length=100, blank=True, null=True)
    address_1 = models.CharField(max_length=500, blank=True, null=True)
    address_2 = models.CharField(max_length=500, blank=True, null=True)
    city = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    nationality = models.CharField(max_length=200, blank=True, null=True)
    zip_code = models.CharField( max_length=200, blank=True, null=True)
    profile_set_up = models.BooleanField(default=False)
    profile_phase = models.CharField(max_length=200, choices=TEST_PHASE, default="live_prod")
    investment_kyc_submitted = models.BooleanField(default=False)
    investement_verified = models.CharField(max_length=200, choices=STATUS_TYPE, default="pending")
    academic_verified = models.BooleanField(default=False)
    ppp_started = models.BooleanField(default=False)
    ppp_verfied = models.BooleanField(default=False)
    pioneer_ppp_member = models.BooleanField(default=False)
    pioneer_ppp_reg_expires = models.DateField(max_length=100, blank=True, null=True)
    cip_pioneer_member = models.BooleanField(default=False)
    remit_inv_funds_to_wallet = models.BooleanField(default=False)
    photo = models.ImageField(upload_to='pipminds/user_profile/', default='default_profile_pics.jpg', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
  
    def __str__(self):
        return self.user.email


    @property
    def last_login(self, *args, **kwargs):
        the_last_login = self.user.last_login
        if the_last_login:
            user_last_login = the_last_login.strftime('%Y-%m-%d %H:%M')
            return user_last_login
        return None

    @property
    def has_active_investment(self, *args, **kwargs):
        user_investments = self.user_investments.filter(active=True)
        if user_investments:
            return True
        return False
    
    @property
    def has_active_investment_sum(self, *args, **kwargs):
        user_investments = self.user_investments.filter(active=True).all()
        if user_investments:
            active_invested_funds = self.user_investments.filter(active=True).aggregate(amount_sum=Sum("amount"))
            return active_invested_funds['amount_sum']
        return 0

    @property
    def get_user_referrals(self, *args, **kwargs):
        referrals_qs = UserReferrals.objects.filter(sponsor=self)
        if referrals_qs.exists():
            return referrals_qs.all()
        return None


    @property
    def get_user_sponsors(self, *args, **kwargs):
        referrals_qs = UserReferrals.objects.filter(downline=self)
        if referrals_qs.exists():
            return referrals_qs.all()
        return None



def profile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        profile = Profile.objects.get_or_create(user=instance)

    profile, created = Profile.objects.get_or_create(
        user=instance)
    if profile.user_code is None or profile.user_code == '':
        profile.user_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 8)))
        profile.save()

post_save.connect(profile_receiver, sender=settings.AUTH_USER_MODEL)


# def handle_profile_changes(sender, instance, **kwargs):
#     profile = Profile.objects.get(user=instance.user)

#     if profile.investement_verified == "approved":
#         send_kyc_verified_email.delay(instance.user.pk)
#     elif profile.investement_verified == "rejected":
#         send_kyc_rejected_email.delay(instance.user.pk)
#     else:
#         pass

# post_save.connect(handle_profile_changes, sender=Profile)






class UserBankAccount(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_bank_account")
    bank_name = models.CharField(blank=True, null=True, max_length=200)
    account_name = models.CharField(blank=True, null=True, max_length=200)
    account_number = models.CharField(blank=True, null=True, max_length=20)
    swift_code  = models.CharField(blank=True, null=True, max_length=20)

    def __str__(self):
        return self.user.user.email

class NextOfKin(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_next_of_kin")
    full_name = models.CharField(blank=True, null=True, max_length=200)
    email = models.CharField(blank=True, null=True, max_length=200)
    phone = models.CharField(blank=True, null=True, max_length=200)

    def __str__(self):
        return self.user.user.email



class Referral(models.Model):
    sponsor_id = models.CharField(max_length=200)
    downline_id = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.sponsor_id
    

class UserReferrals(models.Model):
    sponsor = models.ForeignKey(Profile, on_delete=models.CASCADE,  related_name='sponsor', blank=True, null=True)
    downline = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='downline', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.sponsor.first_name} -> {self.downline.first_name}"

    class Meta:
        unique_together = (('sponsor', 'downline'),)

  

 
DOCUMENT_TYPE = (
    ("passport", "Passport"),
    ("national_id", "National ID"),
    ("driving_license", "Driving License"),
    ("voter_card", "Voters Card")
)

class UserDocument(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_documents")
    doc_type = models.CharField(max_length=200, choices=DOCUMENT_TYPE, default="passport")
    doc_front = models.ImageField(upload_to='pipminds/user_profile/documents/',  blank=True, null=True)
    doc_back = models.ImageField(upload_to='pipminds/user_profile/documents/',  blank=True, null=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.user.email



MEMBERSHIP_CHOICES = (
   
    ('premium', 'Premium'),
    ('free', 'Free')

)

class Membership(models.Model):
    slug = models.SlugField()
    membership_type = models.CharField(
        choices=MEMBERSHIP_CHOICES,
        default='free',
        max_length=30)
    price = models.IntegerField(default=10)

    paystack_plan_id = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self):
        return self.membership_type

class UserMembership(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_membership")
    paystack_customer_id = models.CharField(max_length=40, blank=True, null=True)
    paystack_unique_user_id = models.CharField(max_length=40, blank=True, null=True)
    membership = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.user.username

class Subscription(models.Model):
    user_membership = models.ForeignKey(
        UserMembership, on_delete=models.CASCADE, related_name="user_subscription")
    paystack_subscription_id = models.CharField(max_length=40)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user_membership.user.username

    @property
    def get_created_date(self):
        return self.created_at

    @property
    def get_next_billing_date(self):
        next_billing = self.created_at + timedelta(days=365)
        return next_billing

# The most recent Subscrption Instance txn_code will be thesame value with the Subscription paystack_subscription_id

class SubscriptionInstance(models.Model):
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="user_subscription_instance", blank=True, null=True)
    user = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="profile_subscription_instance", blank=True, null=True)
    txn_code = models.CharField(max_length=200)
    contract_file = models.FileField(upload_to='pipminds/ppp_contracts', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.user.email





def post_save_usermembership_create(sender, instance, created, *args, **kwargs):
    if created:
        UserMembership.objects.get_or_create(user=instance)

    user_membership, created = UserMembership.objects.get_or_create(
        user=instance)


    basic_membership = Membership.objects.get(membership_type='free')
    user_membership.membership = basic_membership
    user_membership.save()


    #comment this out during migrations 
    # if user_membership.paystack_customer_id is None or user_membership.paystack_customer_id == '':
    #     new_customer = paystack.customer.create(email=instance.email)
    #     print(new_customer)
    #     basic_membership = Membership.objects.get(membership_type='free')
    #     if new_customer['status'] == True:
    #         user_membership.paystack_customer_id = new_customer['data']['id']
    #         user_membership.paystack_unique_user_id = new_customer['data']['customer_code']
    #     user_membership.membership = basic_membership
    #     user_membership.save()



post_save.connect(post_save_usermembership_create,
                  sender=settings.AUTH_USER_MODEL)


class UserNotifications(models.Model):
    message = models.CharField(blank=True, null=True, max_length=800)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_notifications", blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)


class SupportTickets(models.Model):
    message = models.CharField(blank=True, null=True, max_length=800)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=200, choices=STATUS_TYPE, default="pending")
    created_at = models.DateTimeField(default=timezone.now)


class UserImportDoc(models.Model):
    doc = models.FileField(upload_to='pipminds/import_documents/admin_import', blank=True, null=True)

    def __str__(self):
        return self.doc