from __future__ import absolute_import, unicode_literals
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.template.loader import render_to_string
from .models import *
from users.models import *


from celery import shared_task
import glob
import os
import requests


@shared_task
def initiated_card_deposit(user_id,txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Transaction.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    subject, from_email, to = 'A New Card Deposit Initiated', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com']
    html_content = render_to_string(
        'events/card_deposit_initiated.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount':amount})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def initiated_manual_deposit(user_id,txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Transaction.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    ref = transaction.txn_code
    subject, from_email, to = 'A New Manual Transfer Deposit Initiated', 'PIPMINDS <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com']
    html_content = render_to_string(
        'events/manual_deposit_initiated.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount, 'ref':ref})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def canceled_manual_deposit(user_id,txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Transaction.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    ref = transaction.txn_code
    subject, from_email, to = 'Manual deposit has been canceled', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com']
    html_content = render_to_string(
        'events/manual_deposit_canceled.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'phone':profile.phone, 'amount': amount, 'ref':ref})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def successful_card_deposit(user_id, txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Transaction.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    subject, from_email, to = 'A New Card Deposit has been Received', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com']
    html_content = render_to_string(
        'events/card_deposit_successful.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def successful_monnify_deposit(user_id, txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Transaction.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    subject, from_email, to = 'A New Monnify Transfer has been Received', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com']
    html_content = render_to_string(
        'events/monnify_deposit_successful.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def send_webhook_value_added(user_id, txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Transaction.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    subject, from_email, to = 'A New Monnify Webhook Value was just added to user', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com' ]
    html_content = render_to_string(
        'events/monnify_webhook_value.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def send_wallet_generated_error(msg):
    subject, from_email, to = 'Wallet Generated Errors', 'PIPMINDS INVEST <hello@pipminds.com>', ['hello@scriptdeskng.com' ]
    html_content = render_to_string(
        'events/wallet_random_error.html', {'message': msg})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()



@shared_task
def referral_profit_withrawal_request(user_id,txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Withdrawal.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    subject, from_email, to = 'New Withdrawal Request', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com']
    html_content = render_to_string(
        'events/referal_withraw_request.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount':amount})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def investment_profit_withrawal_request(user_id, txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Withdrawal.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    subject, from_email, to = 'New Withdrawal Request', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com']
    html_content = render_to_string(
        'events/investment_withraw_request.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def flex_wallet_withrawal_request(user_id, txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Withdrawal.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    subject, from_email, to = 'New Withdrawal Request', 'PIPMINDS INVEST <hello@pipminds.com>', ['account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com']
    html_content = render_to_string(
        'events/flex_wallet_withraw_request.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()



@shared_task
def manual_deposit_approved(user_id, txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Deposit.objects.filter(txn_code=txn_code).first()
    print(transaction)
    amount = transaction.amount
    ref = transaction.txn_code
    subject, from_email, to = 'Manual Deposit Approved', 'PIPMINDS INVEST <hello@pipminds.com>', [user.email]
    html_content = render_to_string(
        'events/manual_deposit_approved.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount, 'ref':ref})
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()

@shared_task
def withdrawal_request_approved(user_id,txn_code):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    transaction = Withdrawal.objects.filter(txn_code=txn_code).first()
    amount = transaction.amount
    ref = transaction.txn_code
    subject, from_email, to = f"{amount} has been credited to your account", 'PIPMINDS INVEST <hello@pipminds.com>', [user.email]
    html_content = render_to_string(
        'events/withdrawal_request_approved.html', {'email': user.email, 'first_name': profile.first_name, 'last_name': profile.last_name, 'amount': amount, 'ref':ref, 'wallet': transaction.wallet })
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def update_monnify_transaction_ref(trans_code, trans_ref):
    the_transaction = Transaction.objects.filter(txn_code=trans_code).first()
    print(f"the transaction code  is {the_transaction.txn_code}")
    print(f"the transaction reference before is {the_transaction.trans_ref}")
    the_transaction.trans_ref = trans_ref
    the_transaction.save()
    print(f"the transaction reference after saving is {the_transaction.trans_ref}")








