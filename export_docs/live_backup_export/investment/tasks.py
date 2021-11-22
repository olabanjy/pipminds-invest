from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.template.loader import render_to_string
from .models import *
from users.models import * 
from wallet.models import *
import random, string
from datetime import timedelta, date, datetime
from dateutil.parser import parse
import pytz

from celery import shared_task
import glob
import os
import requests





@shared_task
def send_investment_started_mail(user_id, plan_id, filename):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    the_plan = UserInvestment.objects.filter(user=profile, pk = plan_id).first()
    contract_file = the_plan.contract_file
    response = requests.get(contract_file.url)
    subject, from_email, to = 'INVESTMENT CONFIRMED', 'PIPMINDS INVEST <hello@pipminds.com>', [
        user.email]
    html_content = render_to_string(
        'events/investment_started.html', {
            'first_name':profile.first_name,
            'last_name':profile.last_name
        })
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.attach(filename, response.content, mimetype="application/pdf")
    msg.send()



@shared_task
def send_investment_started_mail_admin(user_id, plan_id):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    the_plan = UserInvestment.objects.filter(user=profile, pk = plan_id).first()
    subject, from_email, to = 'INVESTMENT CONFIRMED', 'PIPMINDS INVEST <hello@pipminds.com>', [
         'account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com' ]
   
    html_content = render_to_string(
        'events/investment_started_admin.html', {
            'first_name':profile.first_name,
            'last_name':profile.last_name,
            'invested_amount': the_plan.amount,
            'investment_cat': the_plan.plan.category.name
        })
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def send_toup_confirmed_mail(user_id, amount, plan_id, topup_id, filename):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    my_plan = UserInvestment.objects.filter(user=profile, pk = plan_id).first()
    the_topup = UserInvestmentTopups.objects.get(pk=topup_id)
    topup_amount = the_topup.amount
    contract_file = the_topup.contract_file
    response = requests.get(contract_file.url)
    subject, from_email, to = 'INVESTMENT TOP UP CONFIRMED', 'PIPMINDS INVEST <hello@pipminds.com>', [
        user.email]
    # text_content = f" Dear {user.username}. Welcome to Ultra "
    html_content = render_to_string(
        'events/successful_topup_user.html', {
            'first_name':profile.first_name,
            'last_name':profile.last_name,
            'topup_amount': topup_amount,
            'investment_amount': my_plan.amount
        })
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.attach(filename, response.content, mimetype="application/pdf")
    msg.send()

@shared_task
def send_toup_confirmed_mail_admin(user_id, amount, plan_id ):
    user =  User.objects.get(pk=user_id)
    profile = user.profile
    my_plan = UserInvestment.objects.filter(user=profile, pk = plan_id).first()
    topup_amount = amount
    subject, from_email, to = 'NEW INVESTMENT TOP UP', 'PIPMINDS INVEST <hello@pipminds.com>', [
       'account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com' ]
    # text_content = f" Dear {user.username}. Welcome to Ultra "
    html_content = render_to_string( 
        'events/successful_topup_admin.html', {
            'first_name':profile.first_name,
            'last_name':profile.last_name,
            'topup_amount': topup_amount,
            'investment_amount': my_plan.amount,
            'ref_code': my_plan.txn_code
        })
    msg = EmailMessage(subject, html_content, from_email, to)
    msg.content_subtype = "html"
    msg.send()


@shared_task
def credit_cip_active_investments():
    p = lambda x: x/100
    today = datetime.now()
    today = pytz.utc.localize(today)
    
    print(today)
    active_investments = UserInvestment.objects.filter(active=True, completed=False, plan__category__name="CIP")
    if active_investments.exists():
        for investment in active_investments:
            amount = investment.amount
            plan = investment.plan
            percentage = plan.percentage_interest
            maturity_date = investment.maturity_date
            created_date = investment.created_at
            next_payout = investment.next_payout
            daily_percentage = int(percentage) / 30 
            earning = float(amount) *p(daily_percentage)


            investment_earning = UserInvestmentEarnings.objects.filter(plan=investment, active=True, completed=False)
            
            for user_earnings in investment_earning:
                user_investment_wallet = InvestmentWallet.objects.filter(user=user_earnings.user).first()

                if maturity_date and today.date() == maturity_date.date():

                    transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                    if user_earnings.user.remit_inv_funds_to_wallet:
                        user_earnings.amount += Decimal(earning)
                        user_earnings.save()
                        print(f"earning of maturity period is {user_earnings.amount} ")

                        new_payment = Payments.objects.create(txn_code=transaction_code, amount=user_earnings.amount, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

                        new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        #new_capital_payment = Payments.objects.create(txn_code=transaction_code, amount=investment.amount, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"CIP CAPITAL Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
                        
                        #new_capital_tnx = Transaction.objects.create(amount=investment.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                      
                        total_payout = investment.amount + user_earnings.amount
                        
                        user_earnings.plan.profit_earned += earning
                        user_earnings.plan.profit_paid += user_earnings.amount
                    
                        user_earnings.amount = 0
                        user_earnings.completed = True 
                        user_earnings.active = False
                        user_earnings.save()

                        user_earnings.plan.completed = True
                        user_earnings.plan.active = False
                        user_earnings.plan.save()

                        #new_tnx = Transaction.objects.create(amount=total_payout, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')
                        
                        

                        email_profile = user_earnings.user

                        try:
                            
                            subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
                            email_profile.user.email]
                            
                            html_content = render_to_string(
                                'events/cip_complete_investment.html', {
                                    'email': email_profile.user.email,
                                    'first_name': email_profile.first_name,
                                    'last_name':email_profile.last_name,
                                    'investment_display_name': investment.display_name,
                                    'investment_txn_code': investment.txn_code,
                                    'investment_amount': investment.amount,
                                    'inv_maturity_datetime': investment.maturity_date,
                                    'inv_maturity_cat': investment.plan.category.name,
                                    'period': int(investment.maturity_days), 
                                    'inv_maturity_date': datetime.date(investment.maturity_date),
                                    'rollover_starts': f"{(investment.maturity_date + timedelta(minutes=1)).date()}",
                                    'rollover_ends': f"{(investment.maturity_date + timedelta(days=7)).date()}"
                        
                                })
                            msg = EmailMessage(subject, html_content, from_email, to)
                            msg.content_subtype = "html"
                            msg.send()


                        except (ValueError, NameError, TypeError) as error:
                            err_msg = str(error)
                            print(err_msg)
                            
                        except:
                            print("Unexpected Error")
                            
                        
                        
                        print(f"first worked for {user_earnings.user.first_name}")
                    
                    else:
                        print("User is to be paid into bank account ")
                        user_earnings.amount += Decimal(earning)
                        user_earnings.save()
                        print(f"earning of maturity period is {user_earnings.amount} ")
                        total_payout = investment.amount + user_earnings.amount
                        user_earnings.plan.profit_earned += earning
                        user_earnings.plan.profit_paid += user_earnings.amount
                        
                        

                        new_payment = Payments.objects.create(txn_code=transaction_code, amount=user_earnings.amount, user = user_earnings.user, destination="bank_account", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

                        new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        #new_capital_payment = Payments.objects.create(txn_code=transaction_code, amount=investment.amount, user = user_earnings.user, destination="bank_account", status='pending',remark=f"CIP CAPITAL Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
                        
                        #new_capital_tnx = Transaction.objects.create(amount=investment.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        user_earnings.amount = 0
                        user_earnings.completed = True 
                        user_earnings.active = False
                        user_earnings.save()

                        user_earnings.plan.completed = True
                        user_earnings.plan.active = False
                        user_earnings.plan.save()

                        #new_tnx = Transaction.objects.create(amount=total_payout, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')
                     

                        #SEND EMAIL TO USER AND USER HERE 

                        email_profile = user_earnings.user

                        try:
                            
                            subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
                            email_profile.user.email]
                            
                            html_content = render_to_string(
                                'events/cip_complete_investment.html', {
                                    'email': email_profile.user.email,
                                    'first_name': email_profile.first_name,
                                    'last_name':email_profile.last_name,
                                    'investment_display_name': investment.display_name,
                                    'investment_txn_code': investment.txn_code,
                                    'investment_amount': investment.amount,
                                    'inv_maturity_datetime': investment.maturity_date,
                                    'inv_maturity_cat': investment.plan.category.name,
                                    'period': int(investment.maturity_days), 
                                    'inv_maturity_date': datetime.date(investment.maturity_date),
                                    'rollover_starts': f"{(investment.maturity_date + timedelta(minutes=1)).date()}",
                                    'rollover_ends': f"{(investment.maturity_date + timedelta(days=7)).date()}"
                        
                                })
                            msg = EmailMessage(subject, html_content, from_email, to)
                            msg.content_subtype = "html"
                            msg.send()


                        except (ValueError, NameError, TypeError) as error:
                            err_msg = str(error)
                            print(err_msg)
                            
                        except:
                            print("Unexpected Error")
                        
                        



                elif next_payout and today.date() == next_payout.date():
                    transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))

                    if user_earnings.user.remit_inv_funds_to_wallet:
                  
                        payout_this_month = user_earnings.amount

                        new_payment = Payments.objects.create(txn_code=transaction_code, amount=payout_this_month, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

                        new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                   
                        user_earnings.plan.profit_earned += earning
                        user_earnings.plan.profit_paid += payout_this_month
                        user_earnings.amount = earning
                        user_earnings.save()

                        user_earnings.plan.next_payout = today + timedelta(30)
                        user_earnings.plan.save()

                        

                        #SEND EMAIL HERE 
                        
                        email_profile = user_earnings.user
                        try:

                            domain = 'portal.pipminds.com'
                            subject, from_email, to = 'Hurray! Its PayDay', 'PIPMINDS <hello@pipminds.com>', [
                                email_profile.user.email]
    
                            html_content = render_to_string(
                                'events/cip_monthly_interest.html', {
                                    'first_name': email_profile.first_name,
                                    'last_name':email_profile.last_name,
                                    'investment_name': investment.plan.name,
                                    'investment_category': investment.plan.category.name,
                                    'percentage': investment.plan.percentage_interest,
                                    'payout_this_month': payout_this_month, 
                                    'wallet_url': f'http://{domain}/wallet/wallets'
                                    
                                })
                            msg = EmailMessage(subject, html_content, from_email, to)
                            msg.content_subtype = "html"
                            msg.send()

                        except (ValueError, NameError, TypeError) as error:
                            err_msg = str(error)
                            print(err_msg)
                            
                        except:
                            print("Unexpected Error")


                        
                    else:
                        print("User is to be paid into their bank account")
                        payout_this_month = user_earnings.amount

                        new_payment = Payments.objects.create(txn_code=transaction_code, amount=payout_this_month, user = user_earnings.user, destination="bank_account", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

                        new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        user_earnings.plan.profit_earned += earning
                        user_earnings.plan.profit_paid += payout_this_month

                       

                        user_earnings.amount = earning
                        user_earnings.save()
                        user_earnings.plan.next_payout = today + timedelta(30)
                        user_earnings.plan.save()

                        #SEND A MAIL TO ADMIN AND USER HERE 
                        


                    print(f" second worked for {user_earnings.user.first_name}")

                else:
                    user_earnings.amount += Decimal(earning)
                    user_earnings.save()
                    user_earnings.plan.profit_earned += earning
                    user_earnings.plan.save()
                    print(user_earnings)

                    print(f" 3rd and normal worked for {user_earnings.user.first_name}")


            
        #ADD VALUE TO SPONSOR TREE 
        for profile in active_investments:
            user = profile.user
            capital = profile.amount
            if user.get_user_sponsors:
                for fathers in user.get_user_sponsors:
                    dad = fathers.sponsor
                    dad_wallet = ReferralWallet.objects.filter(user=dad).first()
                    earning = float(capital) *p(2)
                    daily_earning = earning / 30
                    # print(daily_earning)
               
                    if dad.ppp_verfied: 
                        if dad.user.user_membership.user_subscription.exists():
                            print(f"subscription status of dad is  {dad.user.user_membership.user_subscription.first().active}")
                            if dad.user.user_membership.user_subscription.first().active == True:
                                if dad.has_active_investment and dad.has_active_investment_sum >= 300000:
                                    dad_wallet.balance += Decimal(daily_earning) 
                                    dad_wallet.save()
                                    user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=dad, amount = Decimal(daily_earning) )
                                    user_ref_earning.save()
                                    new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = dad, txn_method="manual", txn_type='referral_earnings')
                                    new_tnx.save()

                        elif dad.pioneer_ppp_member == True:
                            print(f"dad {dad} is a pioneer ")
                            if dad.has_active_investment and dad.has_active_investment_sum >= 300000:
                                dad_wallet.balance += Decimal(daily_earning) 
                                dad_wallet.save()
                                user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=dad, amount = Decimal(daily_earning) )
                                user_ref_earning.save()
                                new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = dad, txn_method="manual", txn_type='referral_earnings')
                                new_tnx.save()


                        
                    
                    if fathers.sponsor.get_user_sponsors:
                        for grand_fathers in fathers.sponsor.get_user_sponsors:
                            #Add 1% to grand father
                            grand_dad = grand_fathers.sponsor
                            grand_dad_wallet = ReferralWallet.objects.filter(user=grand_dad).first()
                            earning = float(capital) *p(1)
                            daily_earning = earning / 30
                            # print(daily_earning)
                           
                            if grand_dad.ppp_verfied:
                                if grand_dad.user.user_membership.user_subscription.exists():
                                    print(f"subscription status of grandad is  {grand_dad.user.user_membership.user_subscription.first().active}")
                                    if grand_dad.user.user_membership.user_subscription.first().active == True:
                                        if grand_dad.has_active_investment and grand_dad.has_active_investment_sum >= 300000:
                                            grand_dad_wallet.balance += Decimal(daily_earning) 
                                            grand_dad_wallet.save()
                                            user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=grand_dad, amount = Decimal(daily_earning) )
                                            user_ref_earning.save()
                                            new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = grand_dad, txn_method="manual", txn_type='referral_earnings')
                                            new_tnx.save()

                                elif grand_dad.pioneer_ppp_member == True:
                                    print(f"grandad {grand_dad} is a pioneer ")
                                    if grand_dad.has_active_investment and grand_dad.has_active_investment_sum >= 300000:
                                        grand_dad_wallet.balance += Decimal(daily_earning) 
                                        grand_dad_wallet.save()
                                        user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=grand_dad, amount = Decimal(daily_earning) )
                                        user_ref_earning.save()
                                        new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = grand_dad, txn_method="manual", txn_type='referral_earnings')
                                        new_tnx.save()
                                        
                            

                            if grand_fathers.sponsor.get_user_sponsors:
                                for great_grands in grand_fathers.sponsor.get_user_sponsors:
                                    great_grand = great_grands.sponsor
                                    great_grand_wallet = ReferralWallet.objects.filter(user=great_grand).first()
                                    earning = float(capital) *p(0.5)
                                    daily_earning = earning / 30
                                    # print(daily_earning)
                                    if great_grand.ppp_verfied:
                                        if great_grand.user.user_membership.user_subscription.exists():
                                            print(f"subscription status of great_grand is  {great_grand.user.user_membership.user_subscription.first().active}")
                                            if great_grand.user.user_membership.user_subscription.first().active == True:
                                                if great_grand.has_active_investment and great_grand.has_active_investment_sum >= 300000:
                                                    great_grand_wallet.balance += Decimal(daily_earning) 
                                                    great_grand_wallet.save()
                                                    user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=great_grand, amount = Decimal(daily_earning))
                                                    user_ref_earning.save()
                                                    new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = great_grand, txn_method="manual", txn_type='referral_earnings')
                                                    new_tnx.save()
                                        elif great_grand.pioneer_ppp_member == True:
                                            print(f"great_grand {great_grand} is a pioneer ")
                                            if great_grand.has_active_investment and great_grand.has_active_investment_sum >= 300000:
                                                great_grand_wallet.balance += Decimal(daily_earning) 
                                                great_grand_wallet.save()
                                                user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=great_grand, amount = Decimal(daily_earning))
                                                user_ref_earning.save()
                                                new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = great_grand, txn_method="manual", txn_type='referral_earnings')
                                                new_tnx.save()



@shared_task
def credit_hip_active_investments():
    p = lambda x: x/100
    today = datetime.now()
    today = pytz.utc.localize(today)
    
    print(today)
    active_investments = UserInvestment.objects.filter(active=True, completed=False, plan__category__name="HIP")
    if active_investments.exists():
        for investment in active_investments:
            amount = investment.amount
            plan = investment.plan
            percentage = plan.percentage_interest
            maturity_date = investment.maturity_date
            created_date = investment.created_at
            next_payout = investment.next_payout
            maturity_days = investment.maturity_days
            daily_percentage = int(percentage) / maturity_days
            print(daily_percentage)
            earning = float(amount) *p(daily_percentage)
            print(earning)

            investment_earning = UserInvestmentEarnings.objects.filter(plan=investment, active=True, completed=False)
            
            for user_earnings in investment_earning:
                user_investment_wallet = InvestmentWallet.objects.get(user=user_earnings.user)

                if maturity_date and today.date() == maturity_date.date():
                    transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                    if user_earnings.user.remit_inv_funds_to_wallet:
                        user_earnings.amount += Decimal(earning)
                        user_earnings.save()

                        new_payment = Payments.objects.create(txn_code=transaction_code, amount=user_earnings.amount, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"HIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

                        new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        #new_capital_payment = Payments.objects.create(txn_code=transaction_code, amount=investment.amount, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"HIP CAPITAL Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
                        
                        #new_capital_tnx = Transaction.objects.create(amount=investment.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                      
                        total_payout = investment.amount + user_earnings.amount

                        print(f"earning of maturity period is {user_earnings.amount} ")
                        
                        user_earnings.plan.profit_earned += earning
                        user_earnings.plan.profit_paid += user_earnings.amount
                        user_earnings.amount = 0 
                        user_earnings.completed = True 
                        user_earnings.active = False
                        user_earnings.save()

                        user_earnings.plan.completed = True
                        user_earnings.plan.active = False
                        user_earnings.plan.save()
                        print(f" first worked for {user_earnings.user.first_name}")

                        #new_tnx = Transaction.objects.create(amount=total_payout, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        email_profile = user_earnings.user

                        try:

                            subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
                                email_profile.user.email]
    
                            html_content = render_to_string(
                                'events/hip_complete_investment.html', {
                                    'email': email_profile.user.email,
                                    'first_name': email_profile.first_name,
                                    'last_name':email_profile.last_name,
                                    'investment_display_name': investment.display_name,
                                    'investment_txn_code': investment.txn_code,
                                    'investment_amount': investment.amount,
                                    'inv_maturity_datetime': investment.maturity_date,
                                    'inv_maturity_cat': investment.plan.category.name,
                                    'period': int(investment.maturity_days), 
                                    'inv_maturity_date': datetime.date(investment.maturity_date),
                                    'rollover_starts': f"{(investment.maturity_date + timedelta(minutes=1)).date()}",
                                    'rollover_ends': f"{(investment.maturity_date + timedelta(days=7)).date()}"
                                    
                                })
                            msg = EmailMessage(subject, html_content, from_email, to)
                            msg.content_subtype = "html"
                            msg.send()

                        except (ValueError, NameError, TypeError) as error:
                            err_msg = str(error)
                            print(err_msg)
                            
                        except:
                            print("Unexpected Error")

                        

                    else:
                        
                        print("User is to be paid into bank account ")
                        user_earnings.amount += Decimal(earning)
                        user_earnings.save()
                        print(f"earning of maturity period is {user_earnings.amount} ")
                        total_payout = investment.amount + user_earnings.amount
                        user_earnings.plan.profit_earned += earning
                        user_earnings.plan.profit_paid += user_earnings.amount
                        
                        

                        new_payment = Payments.objects.create(txn_code=transaction_code, amount=user_earnings.amount, user = user_earnings.user, destination="bank_account", status='pending',remark=f"HIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

                        new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        #new_capital_payment = Payments.objects.create(txn_code=transaction_code, amount=investment.amount, user = user_earnings.user, destination="bank_account", status='pending',remark=f"HIP CAPITAL Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
                        
                        #new_capital_tnx = Transaction.objects.create(amount=investment.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        user_earnings.amount = 0
                        user_earnings.completed = True 
                        user_earnings.active = False
                        user_earnings.save()

                        user_earnings.plan.completed = True
                        user_earnings.plan.active = False
                        user_earnings.plan.save()

                        #new_tnx = Transaction.objects.create(amount=total_payout, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

                        email_profile = user_earnings.user

                        try:
                            subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
                                email_profile.user.email]
    
                            html_content = render_to_string(
                                'events/hip_complete_investment.html', {
                                    'email': email_profile.user.email,
                                    'first_name': email_profile.first_name,
                                    'last_name':email_profile.last_name,
                                    'investment_display_name': investment.display_name,
                                    'investment_txn_code': investment.txn_code,
                                    'investment_amount': investment.amount,
                                    'inv_maturity_datetime': investment.maturity_date,
                                    'inv_maturity_cat': investment.plan.category.name,
                                    'period': int(investment.maturity_days), 
                                    'inv_maturity_date': datetime.date(investment.maturity_date),
                                    'rollover_starts': f"{(investment.maturity_date + timedelta(minutes=1)).date()}",
                                    'rollover_ends': f"{(investment.maturity_date + timedelta(days=7)).date()}"
                                    
                                })
                            msg = EmailMessage(subject, html_content, from_email, to)
                            msg.content_subtype = "html"
                            msg.send()

                        except (ValueError, NameError, TypeError) as error:
                            err_msg = str(error)
                            print(err_msg)
                            
                        except:
                            print("Unexpected Error")
                        

                else:
                    user_earnings.amount += Decimal(earning)
                    user_earnings.save()
                    user_earnings.plan.profit_earned += earning
                    user_earnings.plan.save()
                    print(user_earnings)

                    print(f" 3rd and normal worked for {user_earnings.user.first_name}")


            
        #ADD VALUE TO SPONSOR TREE 
        for profile in active_investments:
            user = profile.user
            capital = profile.amount
            if user.get_user_sponsors:
                for fathers in user.get_user_sponsors:
                    dad = fathers.sponsor
                    dad_wallet = ReferralWallet.objects.filter(user=dad).first()
                    earning = float(capital) *p(2)
                    daily_earning = earning / maturity_days
                    print(daily_earning)
                    if dad.ppp_verfied:
                        if dad.user.user_membership.user_subscription.exists():
                            print(f"subscription status of dad is  {dad.user.user_membership.user_subscription.first().active}")
                            if dad.user.user_membership.user_subscription.first().active == True:
                                if dad.has_active_investment and dad.has_active_investment_sum >= 300000:
                                    dad_wallet.balance += Decimal(daily_earning) 
                                    dad_wallet.save()
                                    user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=dad, amount = Decimal(daily_earning) )
                                    user_ref_earning.save()
                                    new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = dad, txn_method="manual", txn_type='referral_earnings')
                                    new_tnx.save()
                        elif dad.pioneer_ppp_member == True:
                            print(f" dad {dad} is a pioneer ")
                            if dad.has_active_investment and dad.has_active_investment_sum >= 300000:
                                dad_wallet.balance += Decimal(daily_earning) 
                                dad_wallet.save()
                                user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=dad, amount = Decimal(daily_earning) )
                                user_ref_earning.save()
                                new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = dad, txn_method="manual", txn_type='referral_earnings')
                                new_tnx.save()

                            

                        
                    
                    if fathers.sponsor.get_user_sponsors:
                        for grand_fathers in fathers.sponsor.get_user_sponsors:
                            #Add 1% to grand father
                            grand_dad = grand_fathers.sponsor
                            grand_dad_wallet = ReferralWallet.objects.filter(user=grand_dad).first()
                            earning = float(capital) *p(1)
                            daily_earning = earning / maturity_days
                            print(daily_earning)
                            if grand_dad.ppp_verfied:
                                if grand_dad.user.user_membership.user_subscription.exists():
                                    print(f"subscription status of grand_dad is  {grand_dad.user.user_membership.user_subscription.first().active}")
                                    if grand_dad.user.user_membership.user_subscription.first().active == True:
                                        if grand_dad.has_active_investment and grand_dad.has_active_investment_sum >= 300000:
                                            grand_dad_wallet.balance += Decimal(daily_earning) 
                                            grand_dad_wallet.save()
                                            user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=grand_dad, amount = Decimal(daily_earning) )
                                            user_ref_earning.save()
                                            new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = grand_dad, txn_method="manual", txn_type='referral_earnings')
                                            new_tnx.save()
                                elif grand_dad.pioneer_ppp_member == True:
                                    print(f"grandad {grand_dad}  is a pioneer ")
                                    if grand_dad.has_active_investment and grand_dad.has_active_investment_sum >= 300000:
                                        grand_dad_wallet.balance += Decimal(daily_earning) 
                                        grand_dad_wallet.save()
                                        user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=grand_dad, amount = Decimal(daily_earning) )
                                        user_ref_earning.save()
                                        new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = grand_dad, txn_method="manual", txn_type='referral_earnings')
                                        new_tnx.save()

                            

                            if grand_fathers.sponsor.get_user_sponsors:
                                for great_grands in grand_fathers.sponsor.get_user_sponsors:
                                    great_grand = great_grands.sponsor
                                    great_grand_wallet = ReferralWallet.objects.filter(user=great_grand).first()
                                    earning = float(capital) *p(0.5)
                                    daily_earning = earning / maturity_days
                                    print(daily_earning)
                                    if great_grand.ppp_verfied:
                                        if great_grand.user.user_membership.user_subscription.exists():
                                            print(f"subscription status of grand_dad is  {great_grand.user.user_membership.user_subscription.first().active}")
                                            if great_grand.user.user_membership.user_subscription.first().active == True:
                                                if great_grand.has_active_investment and great_grand.has_active_investment_sum >= 300000:
                                                    great_grand_wallet.balance += Decimal(daily_earning) 
                                                    great_grand_wallet.save()
                                                    user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=great_grand, amount = Decimal(daily_earning))
                                                    user_ref_earning.save()
                                                    new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = great_grand, txn_method="manual", txn_type='referral_earnings')
                                                    new_tnx.save()
                                        elif great_grand.pioneer_ppp_member == True:
                                            print(f"greatgrand {great_grand} is a pioner ")
                                            if great_grand.has_active_investment and great_grand.has_active_investment_sum >= 300000:
                                                great_grand_wallet.balance += Decimal(daily_earning) 
                                                great_grand_wallet.save()
                                                user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=great_grand, amount = Decimal(daily_earning))
                                                user_ref_earning.save()
                                                new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = great_grand, txn_method="manual", txn_type='referral_earnings')
                                                new_tnx.save()
                                        



@shared_task
def send_inv_mature_reminder():

    today = datetime.astimezone(datetime.today())
    
    print(today)
    active_investments = UserInvestment.objects.filter(active=True, completed=False)
    if active_investments.exists():
        for inv in active_investments:
            if datetime.date(today) == (datetime.date(inv.maturity_date) - timedelta(days=7)):
                print("Today is 7 days to expiry date")
                print(f"{inv.user.user.email}")
                print(f"today is {datetime.date(today)} and inv will expire  {datetime.date(inv.maturity_date)}")
                
                email_profile = inv.user
                
                subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
                    email_profile.user.email]

                html_content = render_to_string(
                    'events/inv_mature_at_7days.html', {
                        'email': email_profile.user.email,
                        'first_name': email_profile.first_name,
                        'last_name':email_profile.last_name,
                        'investment_display_name': inv.display_name,
                        'investment_txn_code': inv.txn_code,
                        'investment_amount': inv.amount,
                        'inv_maturity_datetime': inv.maturity_date,
                        'inv_maturity_cat': inv.plan.category.name,
                        'period': int(inv.maturity_days), 
                        'inv_maturity_date': datetime.date(inv.maturity_date),
                        'rollover_starts': f"{(inv.maturity_date + timedelta(days=1)).date()}",
                        'rollover_ends': f"{(inv.maturity_date + timedelta(days=8)).date()}"
                    })
                msg = EmailMessage(subject, html_content, from_email, to)
                msg.content_subtype = "html"
                msg.send()
            elif datetime.date(today) == (datetime.date(inv.maturity_date) - timedelta(days=3)):
                print("Today is 3 days to expiry date")
                print(f"{inv.user.user.email}")
             
                print(f"today is {datetime.date(today)} and inv will expire  {datetime.date(inv.maturity_date)}")
                email_profile = inv.user
             
                subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
                    email_profile.user.email]

                html_content = render_to_string(
                    'events/inv_mature_at_3days.html', {
                        'email': email_profile.user.email,
                        'first_name': email_profile.first_name,
                        'last_name':email_profile.last_name,
                        'investment_display_name': inv.display_name,
                        'investment_txn_code': inv.txn_code,
                        'investment_amount': inv.amount,
                        'inv_maturity_datetime': inv.maturity_date,
                        'inv_maturity_cat': inv.plan.category.name,
                        'period': int(inv.maturity_days), 
                        'inv_maturity_date': datetime.date(inv.maturity_date),
                        'rollover_starts': f"{(inv.maturity_date + timedelta(days=1)).date()}",
                        'rollover_ends': f"{(inv.maturity_date + timedelta(days=8)).date()}"
                    })
                msg = EmailMessage(subject, html_content, from_email, to)
                msg.content_subtype = "html"
                msg.send()


@shared_task
def generate_payment_for_completed_inv():

    today = datetime.astimezone(datetime.today())
    
    print(today)
    active_investments = UserInvestment.objects.filter(active=False, completed=True)
    if active_investments.exists():
        for inv in active_investments:
            if not inv.has_been_rolled_over:
                if datetime.date(today) == inv.get_rollover_ends:
                    print(inv.user.user.email)
                    print(inv.get_rollover_ends)
                    print(f"Generate payment for {inv.user.user.email} ")
                    user_wallet = MainWallet.objects.filter(user=inv.user).first()
                    

                    if inv.plan.category.name == 'CIP':
                        transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                        new_capital_payback_get = CapitalPaybacks.objects.filter(user=inv.user, investment=inv).first()
                        if not new_capital_payback_get:
                            new_capital_payback = CapitalPaybacks.objects.create(user=inv.user, investment=inv)
                            # new_capital_payback_payment = Payments.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, remark="CIP Capital Payback")
                            user_wallet.deposit += int(inv.amount)
                            user_wallet.save()
                            # Send Email to Admin and User 
                            try:
                                # Email to User 
                                subject, from_email, to = 'NOTICE OF CAPITAL PAYBACK !', 'PIPMINDS INVEST<hello@pipminds.com>', [
                                            inv.user.user.email]

                                html_content = render_to_string(
                                    'events/capital_refund_user.html', {
                                        'email': inv.user.user.email,
                                        'first_name': inv.user.first_name,
                                        'last_name':inv.user.last_name,
                                        'investment_display_name': inv.display_name,
                                        'investment_txn_code': inv.txn_code,
                                        'investment_amount': inv.amount,
                                        'inv_maturity_datetime': inv.maturity_date,
                                        'inv_maturity_cat': inv.plan.category.name
                                       
                                    })
                                msg = EmailMessage(subject, html_content, from_email, to)
                                msg.content_subtype = "html"
                                msg.send()




                                
                            except (ValueError, NameError, TypeError) as error:
                                err_msg = str(error)
                                print(err_msg)
                            
                            except:
                                print("Unexpected Error")

                            
                            new_capital_payback_transaction = Transaction.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, txn_method='manual' ,txn_type='withdrawal')
                            new_capital_payback_notification =  UserNotifications.objects.create(user=inv.user, message=f"Your wallet has been credited with a capital refund of {int(inv.amount)} ")

                            try:
                                # Email to Admin 
                                subject, from_email, to = 'NOTICE OF CAPITAL PAYBACK !', 'PIPMINDS INVEST<hello@pipminds.com>', [ 'account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com', 'hello@scriptdeskng.com' ]

                                html_content = render_to_string(
                                    'events/capital_refund_admin.html', {
                                        'email': inv.user.user.email,
                                        'first_name': inv.user.first_name,
                                        'last_name':inv.user.last_name,
                                        'investment_display_name': inv.display_name,
                                        'investment_txn_code': inv.txn_code,
                                        'investment_amount': inv.amount,
                                        'inv_maturity_datetime': inv.maturity_date,
                                        'inv_maturity_cat': inv.plan.category.name
                                       
                                    })
                                msg = EmailMessage(subject, html_content, from_email, to)
                                msg.content_subtype = "html"
                                msg.send()
                                
                            except (ValueError, NameError, TypeError) as error:
                                err_msg = str(error)
                                print(err_msg)
                            
                            except:
                                print("Unexpected Error")

                    elif inv.plan.category.name == 'HIP':
                        transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                        new_capital_payback_get = CapitalPaybacks.objects.filter(user=inv.user, investment=inv).first()
                        if not new_capital_payback_get:
                            new_capital_payback = CapitalPaybacks.objects.create(user=inv.user, investment=inv)
                            user_wallet.deposit += int(inv.amount)
                            user_wallet.save()

                            # Send Email to Admin and User 
                            try:
                                # Email to User 
                                subject, from_email, to = 'NOTICE OF CAPITAL PAYBACK !', 'PIPMINDS INVEST<hello@pipminds.com>', [
                                            inv.user.user.email]

                                html_content = render_to_string(
                                    'events/capital_refund_user.html', {
                                        'email': inv.user.user.email,
                                        'first_name': inv.user.first_name,
                                        'last_name':inv.user.last_name,
                                        'investment_display_name': inv.display_name,
                                        'investment_txn_code': inv.txn_code,
                                        'investment_amount': inv.amount,
                                        'inv_maturity_datetime': inv.maturity_date,
                                        'inv_maturity_cat': inv.plan.category.name
                                       
                                    })
                                msg = EmailMessage(subject, html_content, from_email, to)
                                msg.content_subtype = "html"
                                msg.send()

                                
                            except (ValueError, NameError, TypeError) as error:
                                err_msg = str(error)
                                print(err_msg)
                            
                            except:
                                print("Unexpected Error")

                            # new_capital_payback_payment = Payments.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, remark="HIP Capital Payback")
                            new_capital_payback_transaction = Transaction.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, txn_method='manual' ,txn_type='withdrawal')
                            new_capital_payback_notification =  UserNotifications.objects.create(user=inv.user, message=f"Your wallet has been credited with a capital refund of {int(inv.amount)}")
                            try:
                                # Email to Admin 
                                subject, from_email, to = 'NOTICE OF CAPITAL PAYBACK !', 'PIPMINDS INVEST<hello@pipminds.com>', [ 'account.inv@pipminds.com', 'admin.inv@pipminds.com', 'tech.inv@pipminds.com', 'alban.inv@pipminds.com', 'hello@scriptdeskng.com' ]

                                html_content = render_to_string(
                                    'events/capital_refund_admin.html', {
                                        'email': inv.user.user.email,
                                        'first_name': inv.user.first_name,
                                        'last_name':inv.user.last_name,
                                        'investment_display_name': inv.display_name,
                                        'investment_txn_code': inv.txn_code,
                                        'investment_amount': inv.amount,
                                        'inv_maturity_datetime': inv.maturity_date,
                                        'inv_maturity_cat': inv.plan.category.name
                                       
                                    })
                                msg = EmailMessage(subject, html_content, from_email, to)
                                msg.content_subtype = "html"
                                msg.send()

                         
                            except (ValueError, NameError, TypeError) as error:
                                err_msg = str(error)
                                print(err_msg)
                            
                            except:
                                print("Unexpected Error")




