from __future__ import absolute_import, unicode_literals
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.template.loader import render_to_string
import users.models
# from .models import Profile, Subscription, Membership, UserMembership
from django.contrib.auth.hashers import make_password
import pandas as pd
import time
from datetime import timedelta, date, datetime
import requests


from celery import shared_task
import glob
import os



@shared_task
def send_referal_email_to_sponsor(user_id):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    subject, from_email, to = 'You Got A New Referral', 'PIPMINDS <hello@pipminds.com>', [
        user.email]
 
    html_content = render_to_string(
        'events/new_referral.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def send_profile_verified_email(user_id):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    subject, from_email, to = 'Start you Journey to Financial Freedom', 'PIPMINDS <hello@pipminds.com>', [
        user.email]

    html_content = render_to_string(
        'events/profile_set_up_success.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def send_kyc_submitted_email(user_id):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    subject, from_email, to = 'KYC Submitted', 'PIPMINDS <hello@pipminds.com>', [
        user.email]
   
    html_content = render_to_string(
        'events/kyc_submitted.html', {})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def send_kyc_submitted_email_admin(user_id):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    subject, from_email, to = 'KYC Submitted', 'PIPMINDS <hello@pipminds.com>', [
       'hello@scriptdeskng.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com' ]
  
    html_content = render_to_string(
        'events/kyc_submitted_admin.html', {'first_name':profile.first_name, 'last_name':profile.last_name })
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def send_kyc_verified_email(user_id):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    subject, from_email, to = 'KYC Verified', 'PIPMINDS <hello@pipminds.com>', [
        user.email]
  
    html_content = render_to_string(
        'events/kyc_verified.html', {})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def send_kyc_rejected_email(user_id):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    subject, from_email, to = 'KYC Rejected', 'PIPMINDS <hello@pipminds.com>', [
        user.email]
   
    html_content = render_to_string(
        'events/kyc_rejected.html', {})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def send_congratulations_email(user_id, plan_id, filename):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    the_sub = users.models.SubscriptionInstance.objects.filter(pk=plan_id, user=profile).first()
    contract_file = the_sub.contract_file
    response = requests.get(contract_file.url)
    subject, from_email, to = 'Welcome to Pipminds Partnership Program', 'PIPMINDS <hello@pipminds.com>', [
        user.email]
    
    html_content = render_to_string(
        'events/ppp_sub_successful.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.attach(filename, response.content, mimetype="application/pdf")
    msg.send()

# @shared_task
# def send_receipt(user_id, membership_id):
#     user =  User.objects.get(pk=user_id)
#     user_membership = UserMembership.objects.get(pk=membership_id)
#     plan = user_membership.membership.membership_type
#     price = user_membership.membership.price
#     profile = user.profile
#     subject, from_email, to = 'ULTRA Receipt', 'ULTRA NG <hello@ultra.ng>', [
#         user.email]
#     # text_content = f" Dear {user.username}. Welcome to Ultra "
#     html_content = render_to_string(
#         'events/receipt.html', {'email': user.email, 'plan':plan, 'price':price})
#     msg = EmailMessage(subject, html_content, from_email, to)
#     msg.content_subtype = "html"
#     msg.send()




@shared_task
def send_ppp_sub_reminder():
    today = datetime.astimezone(datetime.today())
    print(today)
    active_subs = users.models.Subscription.objects.filter(active=True)
    if active_subs.exists():
        for sub in active_subs:
            if datetime.date(today) == (datetime.date(sub.get_next_billing_date) - timedelta(days=7)):
                print("Today is 7 days to expiry date")
                print(f"{sub.user_membership.user.email}")
                print(f"today is {datetime.date(today)} and inv will expire  {datetime.date(sub.get_next_billing_date)}")
                
                email_profile = sub.user_membership.user.profile
                
                subject, from_email, to = 'NOTICE OF PPP SUBSCRIPTION!', 'PIPMINDS <hello@pipminds.com>', [
                    email_profile.user.email]

                html_content = render_to_string(
                    'events/ppp_expires_at_7days.html', {
                        'email': email_profile.user.email,
                        'first_name': email_profile.first_name,
                        'last_name':email_profile.last_name,
                        'ppp_ends': f"{sub.get_next_billing_date}"
                    })
                msg = EmailMessage(subject, html_content, from_email, to)
                msg.content_subtype = "html"
                msg.send()
            elif datetime.date(today) == (datetime.date(sub.get_next_billing_date) - timedelta(days=3)):
                print("Today is 3 days to expiry date")
                print(f"{sub.user_membership.user.email}")
             
                print(f"today is {datetime.date(today)} and inv will expire  {datetime.date(sub.get_next_billing_date)}")
                email_profile = sub.user_membership.user.profile
             
                subject, from_email, to = 'NOTICE OF PPP SUBSCRIPTION!', 'PIPMINDS <hello@pipminds.com>', [
                    email_profile.user.email]

                html_content = render_to_string(
                    'events/ppp_expires_at_3_days.html', {
                       'email': email_profile.user.email,
                        'first_name': email_profile.first_name,
                        'last_name':email_profile.last_name,
                        'ppp_ends': f"{sub.get_next_billing_date}"
                    })
                msg = EmailMessage(subject, html_content, from_email, to)
                msg.content_subtype = "html"
                msg.send()


@shared_task
def end_ppp_subs():

    today = datetime.astimezone(datetime.today())
    
    print(today)
    active_subs = users.models.Subscription.objects.filter(active=True)
    if active_subs.exists():
        for sub in active_subs:
            if datetime.date(today) == datetime.date(sub.get_next_billing_date):
                print("Today is expiry date")
                print(f"{sub.user_membership.user.email}")
                print(f"today is {datetime.date(today)} and inv will expire  {datetime.date(sub.get_next_billing_date)}")
                
                email_profile = sub.user_membership.user.profile

                sub.active = False
                sub.save()


                free_membership = users.models.Membership.objects.filter(
                    membership_type='free').first()
                user_membership = users.models.UserMembership.objects.filter(user=sub.user_membership.user).first()
                user_membership.membership = free_membership
                user_membership.save()

                
                subject, from_email, to = 'NOTICE OF PPP SUBSCRIPTION!', 'PIPMINDS <hello@pipminds.com>', [
                    email_profile.user.email]

                html_content = render_to_string(
                    'events/ppp_expired_today.html', {
                        'email': email_profile.user.email,
                        'first_name': email_profile.first_name,
                        'last_name':email_profile.last_name,
                        'ppp_ends': f"{sub.get_next_billing_date}"
                    })
                msg = EmailMessage(subject, html_content, from_email, to)
                msg.content_subtype = "html"
                msg.send()


@shared_task
def end_ppp_pioneers_subs():

    today = datetime.astimezone(datetime.today())
    
    print(today)
    active_pioneers = users.models.Profile.objects.filter(pioneer_ppp_member=True)
    if active_pioneers.exists():
        for prof in active_pioneers:
            if prof.pioneer_ppp_reg_expires != None:
                if datetime.date(today) == prof.pioneer_ppp_reg_expires:
                    print(f"Today is expiry date {prof.pioneer_ppp_reg_expires} ")
                    
                    prof.pioneer_ppp_member = False 
                    prof.save()


                    email_profile = prof

                    free_membership = users.models.Membership.objects.filter(
                        membership_type='free').first()
                    user_membership = users.models.UserMembership.objects.filter(user=prof.user).first()
                    user_membership.membership = free_membership
                    user_membership.save()

                    
                    subject, from_email, to = 'NOTICE OF PPP SUBSCRIPTION!', 'PIPMINDS <hello@pipminds.com>', [
                        email_profile.user.email]

                    html_content = render_to_string(
                        'events/ppp_expired_today.html', {
                            'email': email_profile.user.email,
                            'first_name': email_profile.first_name,
                            'last_name':email_profile.last_name
                           
                        })
                    msg = EmailMessage(subject, html_content, from_email, to)
                    msg.content_subtype = "html"
                    msg.send()
                



