from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, reverse, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.core.files import File
from django.template.loader import render_to_string, get_template
from django.template import RequestContext
from django.utils.encoding import force_bytes
from django.db.models import Sum
import random, string, os
from datetime import timedelta, date, datetime
from dateutil.parser import parse
import pytz
from decimal import Decimal
from django.contrib.sites.models import Site
from django.views.defaults import page_not_found

from io import BytesIO

from .utils import *

from .models import *
from .tasks import *

from users.models import *
from wallet.models import *





def error404(request, exception):
    return page_not_found(request, exception, 'errors/404.html')



def error500(request):
    return render(request, 'errors/500.html')


class Dashboard(View):
    def get(self, request, *args, **kwargs):


        profile = Profile.objects.get(user=self.request.user)

        if not profile.profile_set_up:
            return redirect('users:profile-set-up')

        if not profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
        
        if profile.investement_verified == 'pending':
            print("KYC Pending")
            return redirect('investment:kyc-pending')

        elif profile.investement_verified == 'rejected':
            print("KYC Rejected")
            return redirect('investment:kyc-rejected')

        template = 'home/index-invest.html' 

      
        user_total_invested_funds = UserInvestment.objects.filter(user=profile, active=True).aggregate(amount_sum=Sum("amount"))
        user_total_profit = UserInvestmentEarnings.objects.filter(user=profile, active=True).aggregate(amount_sum=Sum("amount"))

        today = datetime.now().date()
        print(today)
        dollar_rate = ExchangeRates.objects.filter(name='USD').first()

        portfolio = 0
        if user_total_invested_funds['amount_sum'] and user_total_profit['amount_sum'] != None:
            portfolio = user_total_invested_funds['amount_sum'] + user_total_profit['amount_sum']

        user_profits = UserInvestmentEarnings.objects.filter(user=profile, active=True).all()
        user_investments = UserInvestment.objects.filter(user=profile).order_by('-id').all()

        print(user_total_invested_funds['amount_sum'])
        print(user_total_profit['amount_sum'])
        print(user_investments)

        user_payouts = Payments.objects.filter(user=profile).all()
        print(user_payouts)

        # print(user_profits)
        context = {
            'user_total_invested_funds': user_total_invested_funds['amount_sum'],
            'user_total_profit': user_total_profit['amount_sum'],
            'user_profits': user_profits,
            'user_investments': user_investments,
            'portfolio': portfolio, 
             'dollar_rate_val': dollar_rate.rate_to_base,
             'user_payouts':user_payouts,
             'today':today
        }
        return render(self.request, template, context)




@login_required
def update_kyc(request):
    template = 'investment/kyc_notify.html'

    return render(request,template)

@login_required
def kyc_pending(request):

    if request.user.profile.investement_verified == 'approved':
        print("KYC Approved")
        return redirect('investment:dashboard')
    
    elif request.user.profile.investement_verified == 'rejected':
        print("KYC Pending")
        return redirect('investment:kyc-rejected')

    template = 'investment/kyc_pending.html'

    return render(request,template)

@login_required
def kyc_rejected(request):

    if request.user.profile.investement_verified == 'pending':
        print("KYC Pending")
        return redirect('investment:kyc-pending')

    elif request.user.profile.investement_verified == 'approved':
        print("KYC Approved")
        return redirect('investment:dashboard')


    template = 'investment/kyc_rejected.html'

    return render(request,template)

class InvestmentPlans(View):

    def get(self, request, *args, **kwargs):

        profile = Profile.objects.get(user=self.request.user)

        if not profile.profile_set_up:
            return redirect('users:profile-set-up')

        if not profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
        
        if profile.investement_verified == 'pending':
            print("KYC Pending")
            return redirect('investment:kyc-pending')
        elif profile.investement_verified == 'rejected':
            print("KYC Rejected")
            return redirect('investment:kyc-rejected')

        template = 'investment/plans.html'
        err_msgs = ''

        plans = InvestmentPlan.objects.filter(active=True).all().order_by("id")
        context = {
            'plans': plans
           
        }
 
        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):
        selected_plan  = self.request.POST.get('plan')
        print(selected_plan)
        selected_investment_plan = InvestmentPlan.objects.filter(pk=selected_plan).first()
        print(selected_investment_plan)

        if selected_plan:
            print("Plan selected")
            if selected_investment_plan:
                past_investments = UserInvestment.objects.filter(user=self.request.user.profile, plan = selected_investment_plan, active=True).aggregate(amount_sum=Sum("amount"))
                has_invested = past_investments['amount_sum']
                print(f"past investment of user is {has_invested}")
                if selected_investment_plan.max_investment:
                    if has_invested and  has_invested > selected_investment_plan.max_investment:
                        print("Please choose a diff plan ")
                        messages.error(self.request, f"Please choose a different plan. Your Accumulated investment has exceeded the selected plan max investment ")
                        return HttpResponseRedirect(reverse("investment:plans"))

                return redirect(reverse('investment:process_plan', kwargs= {'plan_id': selected_investment_plan.pk}))
        elif selected_plan is None:
            print("Nothing was selected")
            messages.error(self.request, f"Please select an investment! ")
            return HttpResponseRedirect(reverse("investment:plans"))
    
    

        return HttpResponseRedirect(reverse("investment:plans"))


# MAINTENANCE COMPLETE - 27/02/2021
class ProcessInvestment(View):

    def get(self, request, plan_id, *args, **kwargs):

        date_today  =  datetime.now()
        print(date_today)
        profile = Profile.objects.get(user=self.request.user)

        if not profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
        
        if profile.investement_verified == 'pending':
            print("KYC Pending")
            return redirect('investment:kyc-pending')
        elif profile.investement_verified == 'rejected':
            print("KYC Rejected")
            return redirect('investment:kyc-rejected')


        if (profile.address_1, profile.address_2, profile.state, profile.nationality) == None:
            print(profile.address_1)
            print(profile.address_2)
            print(profile.state)
            print(profile.nationality)
            print("Address not complete")
            messages.error(self.request, f"You need to complete location details to invest. Make sure your Address Line 1, Address Line 2, State and Country are up to date!")
            return redirect('users:profile-settings')
        else:
            print("Address complete!")


        
        
        the_plan = InvestmentPlan.objects.filter(pk=plan_id).first()

 
        template = 'investment/process_form.html'

        wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
        print(wallet)
        wallet_deposit = wallet.deposit
        

        if not wallet_deposit >= the_plan.min_investment:
            messages.error(self.request, f"You cannot afford this plan. Wallet balance:{wallet_deposit}")
            return redirect('investment:plans')

        
            

 
        context = {
            'the_plan': the_plan,
            'wallet_deposit': wallet_deposit,
            'date_today': date_today
        }

        return render(self.request, template, context)
    
    def post(self, request, *args, **kwargs):
        
        wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
        wallet_deposit = wallet.deposit
        amount  = self.request.POST.get('iv-amount')
        plan_id  = self.request.POST.get('plan_id')
        maturity  = self.request.POST.get('maturity')
        t_and_c  = self.request.POST.get('t_and_c')
        display_name = self.request.POST.get('display_name')

        plan = InvestmentPlan.objects.filter(pk = plan_id).first()

        if amount and maturity: 
            if t_and_c:
                past_investments = UserInvestment.objects.filter(user=self.request.user.profile, plan = plan, active=True).aggregate(amount_sum=Sum("amount"))
                if past_investments:
                    has_invested = past_investments['amount_sum']
                    print(f" past investment of user is {has_invested}")
                    if plan.max_investment or plan.max_investment != None:
                        if has_invested and (has_invested + int(amount)) > plan.max_investment:
                            print("Please choose a diff plan ")
                            messages.info(self.request, f"Please input a lesser amount or choose a different plan. Your Accumulated investment for this plan has exceeded the plan max investment ")
                            return HttpResponseRedirect(reverse("investment:process_plan", kwargs={'plan_id': plan.pk }))
                    else:
                        print("Plan maximum does not exist")
                if plan.max_investment and plan.max_investment != None:
                    if plan.min_investment > int(amount) or plan.max_investment < int(amount):
                        print("Has to be within min and max")
                        messages.warning(self.request, f"Amount to invest must be between {plan.min_investment} and {plan.max_investment} ")
                        return HttpResponseRedirect(reverse("investment:process_plan", kwargs={'plan_id': plan.pk }))
                    elif int(amount) > wallet.deposit:
                        messages.warning(self.request, f"You do not have enough fund to proceed, please fund your wallet or input a lesser amount!")
                        print("not enough money ")
                        return HttpResponseRedirect(reverse("investment:process_plan", kwargs={'plan_id': plan.pk }))
                    else:
                        wallet.deposit -= int(amount) 
                        wallet.save() 
                        transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                        # maturity_date = datetime.now() + timedelta(int(plan.maturity_period))
                        new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                        new_user_investment.save()
                        if display_name or display_name != None:
                            new_user_investment.display_name = display_name
                            new_user_investment.save()
                        new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                        new_user_earning.save()
                        matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                        new_user_investment.maturity_date = matured_at
                        if plan.category.name == "CIP":
                            new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                        elif plan.category.name == "HIP":
                            new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                        new_user_investment.save()



                        new_notification = UserNotifications(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")
                        new_notification.save()
                        

                        if plan.category.name == "CIP":
                            contract_data = {
                                'first_name': self.request.user.profile.first_name,
                                'last_name': self.request.user.profile.last_name,
                                'today': datetime.astimezone(datetime.today()) ,
                                'address_1': self.request.user.profile.address_1,
                                'address_2': self.request.user.profile.address_2,
                                'city': self.request.user.profile.city,
                                'state': self.request.user.profile.state,
                                'amount': int(amount),
                                'period': int(int(new_user_investment.maturity_days)/30),
                                'plan_name': plan.name,
                                'plan_percentage': plan.percentage_interest,
                                'plan_min': int(plan.min_investment),
                                'plan_max': int(plan.max_investment)                            
                            }
                            
                            contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                            new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code, contract_data)

                            send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                            send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                        
                        elif plan.category.name == "HIP":
                            contract_data = {
                                'first_name': self.request.user.profile.first_name,
                                'last_name': self.request.user.profile.last_name,
                                'today': datetime.astimezone(datetime.today()) ,
                                'address_1': self.request.user.profile.address_1,
                                'address_2': self.request.user.profile.address_2,
                                'city': self.request.user.profile.city,
                                'state': self.request.user.profile.state,
                                'amount': int(amount),
                                'period': int(int(new_user_investment.maturity_days)/30),
                                'plan_name': plan.name,
                                'plan_percentage': plan.percentage_interest
                               

                            }

                            contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                            new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                            send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                            send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)


                        return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))
                else:
                    if plan.min_investment > int(amount):
                        print("Has to be within min and max")
                        messages.warning(self.request, f"Amount to invest must be more than {plan.min_investment}")
                        return HttpResponseRedirect(reverse("investment:process_plan", kwargs={'plan_id': plan.pk }))
                    elif int(amount) > wallet.deposit:
                        messages.warning(self.request, f"You do not have enough fund to proceed, please fund your wallet or input a lesser amount!")
                        print("not enough money ")
                        return HttpResponseRedirect(reverse("investment:process_plan", kwargs={'plan_id': plan.pk }))
                    else:
                        wallet.deposit-= int(amount) 
                        wallet.save() 
                        transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                        new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                        new_user_investment.save()
                        if display_name or display_name != None:
                            new_user_investment.display_name = display_name
                            new_user_investment.save()
                        new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                        new_user_earning.save()
                        matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                        new_user_investment.maturity_date = matured_at
                        if plan.category.name == "CIP":
                            new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                        elif plan.category.name == "HIP":
                            new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                        new_user_investment.save()

                        new_notification = UserNotifications(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")
                        new_notification.save()

                        if plan.category.name == "CIP":
                            contract_data = {
                                'first_name': self.request.user.profile.first_name,
                                'last_name': self.request.user.profile.last_name,
                                'today': datetime.astimezone(datetime.today()) ,
                                'address_1': self.request.user.profile.address_1,
                                'address_2': self.request.user.profile.address_2,
                                'city': self.request.user.profile.city,
                                'state': self.request.user.profile.state,
                                'amount': int(amount),
                                'period': int(int(new_user_investment.maturity_days)/30),
                                'plan_name': plan.name,
                                'plan_percentage': plan.percentage_interest,
                                'plan_min': int(plan.min_investment),
                                'plan_max': ''
                            

                            }

                            contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                            new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                            send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                            send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                        
                        elif plan.category.name == "HIP":
                            contract_data = {
                                'first_name': self.request.user.profile.first_name,
                                'last_name': self.request.user.profile.last_name,
                                'today': datetime.astimezone(datetime.today()) ,
                                'address_1': self.request.user.profile.address_1,
                                'address_2': self.request.user.profile.address_2,
                                'city': self.request.user.profile.city,
                                'state': self.request.user.profile.state,
                                'amount': int(amount),
                                'period': int(int(new_user_investment.maturity_days)/30),
                                'plan_name': plan.name,
                                'plan_percentage': plan.percentage_interest
                              
                            
                            }

                            contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                            new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                            send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                            send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)


                        return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))
            else:
                messages.info(self.request, f" You have to agree to Terms and Condition to proceed!")
                return HttpResponseRedirect(reverse("investment:process_plan", kwargs={'plan_id': plan.pk }))
        
        return HttpResponseRedirect(reverse("investment:process_plan", kwargs={'plan_id': plan.pk }))







#ROLLOVER PROCESSING FEATURE COMPLETED - 04/04/2021
class RolloverPlans(View):

    def get(self, request, inv_txn_code, *args, **kwargs):

        profile = Profile.objects.get(user=self.request.user)

        if not profile.profile_set_up:
            return redirect('users:profile-set-up')

        if not profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
        
        if profile.investement_verified == 'pending':
            print("KYC Pending")
            return redirect('investment:kyc-pending')
        elif profile.investement_verified == 'rejected':
            print("KYC Rejected")
            return redirect('investment:kyc-rejected')

        template = 'investment/rollover_plans.html'
        err_msgs = ''

        old_inv = UserInvestment.objects.get(txn_code = inv_txn_code)
        old_inv_amount = int(old_inv.amount)

        plans = InvestmentPlan.objects.filter(active=True).all().order_by("id")
        context = {
            'plans': plans,
            'old_inv_amount':old_inv_amount,
            'old_inv':old_inv
           
        }
 
        return render(self.request, template, context)

    def post(self, request, inv_txn_code,  *args, **kwargs):
        selected_plan  = self.request.POST.get('plan')
        print(selected_plan)
        selected_investment_plan = InvestmentPlan.objects.filter(pk=selected_plan).first()
        print(selected_investment_plan)

        if selected_plan:
            print("Plan selected")
            if selected_investment_plan:
                past_investments = UserInvestment.objects.filter(user=self.request.user.profile, plan = selected_investment_plan, active=True).aggregate(amount_sum=Sum("amount"))
                has_invested = past_investments['amount_sum']
                print(f"past investment of user is {has_invested}")
                if selected_investment_plan.max_investment:
                    if has_invested and  has_invested > selected_investment_plan.max_investment:
                        print("Please choose a diff plan ")
                        messages.error(self.request, f"Please choose a different plan. Your Accumulated investment has exceeded the selected plan max investment ")
                        return HttpResponseRedirect(reverse("investment:rollover_plans"))

                return redirect(reverse('investment:process_rollover', kwargs= {'plan_id': selected_investment_plan.pk, 'inv_txn_code':inv_txn_code }))
        elif selected_plan is None:
            print("Nothing was selected")
            messages.error(self.request, f"Please select an investment plan to proceed! ")
            return HttpResponseRedirect(reverse("investment:rollover_plans", kwargs={'inv_txn_code':inv_txn_code}))
    
    

        return HttpResponseRedirect(reverse("investment:rollover_plans", kwargs={'inv_txn_code':inv_txn_code}))


#ROLLOVER PROCESSING FEATURE COMPLETED - 10/03/2021
class ProcessRollover(View):

    def get(self, request, plan_id, inv_txn_code, *args, **kwargs):

        date_today  =  datetime.now()
    
        profile = Profile.objects.get(user=self.request.user)

        old_inv = UserInvestment.objects.get(txn_code = inv_txn_code)
        old_inv_amount = int(old_inv.amount)

        selected_plan = InvestmentPlan.objects.get(pk=plan_id)

        if not profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
        
        if profile.investement_verified == 'pending':
            print("KYC Pending")
            return redirect('investment:kyc-pending')
        elif profile.investement_verified == 'rejected':
            print("KYC Rejected")
            return redirect('investment:kyc-rejected')

        if old_inv.has_been_rolled_over == True:
            print("Already rollerd over")
            return redirect('investment:dashboard')



        if (profile.address_1, profile.address_2, profile.state, profile.nationality) == None:
            print(profile.address_1)
            print(profile.address_2)
            print(profile.state)
            print(profile.nationality)
            print("Address not complete")
            messages.error(self.request, f"You need to complete location details to invest. Make sure your Address Line 1, Address Line 2, State and Country are up to date!")
            return redirect('users:profile-settings')
        else:
            print("Address complete!")

        template = 'investment/process_rollover.html'

        

        wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
    
        wallet_deposit = wallet.deposit



        context = {
            'date_today': date_today,
            'old_inv': old_inv,
            'old_inv_amount': old_inv_amount,
            'wallet_deposit':wallet_deposit,
            'selected_plan':selected_plan
        }

        return render(self.request, template, context)
 
    def post(self, request, *args, **kwargs):
        wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
        wallet_deposit = wallet.deposit
        amount  = self.request.POST.get('iv-amount')
        plan_txn_code  = self.request.POST.get('plan_id')
        maturity  = self.request.POST.get('maturity')
        t_and_c  = self.request.POST.get('t_and_c')
        display_name = self.request.POST.get('display_name')
        selected_plan = self.request.POST.get('selected_plan')

        old_inv = UserInvestment.objects.get(txn_code=plan_txn_code)
        print(old_inv.txn_code)

        plan = InvestmentPlan.objects.filter(pk = selected_plan).first()
        print(plan.name)

        if amount and maturity:
            if t_and_c:
                pass
                past_investments = UserInvestment.objects.filter(user=self.request.user.profile, plan = plan, active=True).aggregate(amount_sum=Sum("amount"))
                if past_investments:
                    has_invested = past_investments['amount_sum']
                    print(f"past investment of user is {has_invested}")
                    if plan.max_investment or plan.max_investment != None:
                        if has_invested and (has_invested + int(amount)) > plan.max_investment:
                            print("Please choose a diff plan ")
                            messages.info(self.request, f"Your Accumulated investment for this plan has exceeded the plan max investment ")
                            return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code':old_inv.txn_code }))
                    else:
                        print("Plan maximum does not exist")
                #check if its exact amount as old investment
                if int(old_inv.amount) == int(amount):
                    print("Investing same old amount")

                    if plan.max_investment and plan.max_investment != None:
                        if plan.min_investment > int(amount) or plan.max_investment < int(amount):
                            print("Has to be within min and max")
                            messages.warning(self.request, f"Amount to invest must be between {plan.min_investment} and {plan.max_investment} ")
                            return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code':old_inv.txn_code }))
                        else:
                            check_roll = UserInvestmentRollovers.objects.filter(old_investment = old_inv, user =self.request.user.profile)
                            if check_roll.exists():
                                print('Rollover already exists') 
                                return HttpResponseRedirect(reverse("investment:dashboard"))
                            else:
                                transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                                # maturity_date = datetime.now() + timedelta(int(plan.maturity_period))
                                new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                                new_user_investment.save()
                                if display_name or display_name != None:
                                    new_user_investment.display_name = display_name
                                    new_user_investment.save()
                                new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                                new_user_earning.save()
                                matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.maturity_date = matured_at
                                new_user_investment.is_rollover = True
                                if plan.category.name == "CIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                                elif plan.category.name == "HIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.save()

                                old_inv.has_been_rolled_over = True
                                old_inv.save()

                                new_rollover = UserInvestmentRollovers.objects.create(old_investment=old_inv, new_investment=new_user_investment, user=self.request.user.profile)





                                new_investment_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")

                                new_rollover_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Rollover of {old_inv.txn_code} has been activated")

                                
                                

                                if plan.category.name == "CIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest,
                                        'plan_min': int(plan.min_investment),
                                        'plan_max': int(plan.max_investment)                            
                                    }
                                    
                                    contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                    new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code, contract_data)

                                    #send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    #send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                                
                                elif plan.category.name == "HIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest
                                    

                                    }

                                    contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                    new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                                    send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)


                                return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))
                    else:
                        if plan.min_investment > int(amount):
                            print("Has to be within min and max")
                            messages.warning(self.request, f"Amount to invest must be more than {plan.min_investment}")
                            return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={ 'plan_id': plan.pk, 'inv_txn_code': old_inv.txn_code }))
                        else:
                            check_roll = UserInvestmentRollovers.objects.filter(old_investment = old_inv, user =self.request.user.profile)
                            if check_roll.exists():
                                print('Rollover already exists') 
                                return HttpResponseRedirect(reverse("investment:dashboard"))
                            else:
                                transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                                new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                                new_user_investment.save()
                                if display_name or display_name != None:
                                    new_user_investment.display_name = display_name
                                    new_user_investment.save()
                                new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                                new_user_earning.save()
                                matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.maturity_date = matured_at
                                new_user_investment.is_rollover = True
                                if plan.category.name == "CIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                                elif plan.category.name == "HIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.save()

                                old_inv.has_been_rolled_over = True
                                old_inv.save()

                                new_rollover = UserInvestmentRollovers.objects.create(old_investment=old_inv, new_investment=new_user_investment, user=self.request.user.profile)

                                new_investment_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")

                                new_rollover_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Rollover of {old_inv.txn_code} has been activated")

                                if plan.category.name == "CIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest,
                                        'plan_min': int(plan.min_investment),
                                        'plan_max': ''
                                    

                                    }

                                    contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                    new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                                    send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                                
                                elif plan.category.name == "HIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest
                                
                                    }

                                    contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"
                                    new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)
                                    send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)

                                return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))
                #check if it was topped up 
                elif int(old_inv.amount) < int(amount):
                    the_diff = int(amount) - int(old_inv.amount)
                    print(f"You invested more so you added {the_diff}")
                    if the_diff > wallet.deposit:
                        messages.warning(self.request, f"You do not have enough fund to proceed, please fund your wallet to proceed !")
                        print("not enough money")
                        return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code':old_inv.txn_code }))
                    else:
                        if plan.max_investment and plan.max_investment != None:
                            if plan.min_investment > int(amount) or plan.max_investment < int(amount):
                                print("Has to be within min and max")
                                messages.warning(self.request, f"Amount to invest must be between {plan.min_investment} and {plan.max_investment} ")
                                return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code':old_inv.txn_code }))
                            else:
                                check_roll = UserInvestmentRollovers.objects.filter(old_investment = old_inv, user =self.request.user.profile)
                                if check_roll.exists():
                                    print('Rollover already exists') 
                                    return HttpResponseRedirect(reverse("investment:dashboard"))
                                else:
                                    wallet.deposit -= the_diff
                                    wallet.save()
                                    transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                                    # maturity_date = datetime.now() + timedelta(int(plan.maturity_period))
                                    new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                                    new_user_investment.save()
                                    if display_name or display_name != None:
                                        new_user_investment.display_name = display_name
                                        new_user_investment.save()
                                    new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                                    new_user_earning.save()
                                    matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                    new_user_investment.maturity_date = matured_at
                                    new_user_investment.is_rollover = True
                                    if plan.category.name == "CIP":
                                        new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                                    elif plan.category.name == "HIP":
                                        new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                    new_user_investment.save()

                                    old_inv.has_been_rolled_over = True
                                    old_inv.save()

                                    new_rollover = UserInvestmentRollovers.objects.create(old_investment=old_inv, new_investment=new_user_investment, user=self.request.user.profile)

                                    new_investment_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")

                                    new_rollover_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Rollover of {old_inv.txn_code} has been activated")

                                    new_deduction_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Your flex wallet has been debited with a sum of {the_diff}")
                                    
                                    

                                    if plan.category.name == "CIP":
                                        contract_data = {
                                            'first_name': self.request.user.profile.first_name,
                                            'last_name': self.request.user.profile.last_name,
                                            'today': datetime.astimezone(datetime.today()) ,
                                            'address_1': self.request.user.profile.address_1,
                                            'address_2': self.request.user.profile.address_2,
                                            'city': self.request.user.profile.city,
                                            'state': self.request.user.profile.state,
                                            'amount': int(amount),
                                            'period': int(int(new_user_investment.maturity_days)/30),
                                            'plan_name': plan.name,
                                            'plan_percentage': plan.percentage_interest,
                                            'plan_min': int(plan.min_investment),
                                            'plan_max': int(plan.max_investment)                            
                                        }
                                        
                                        contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                        new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code, contract_data)

                                        send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                        send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                                    
                                    elif plan.category.name == "HIP":
                                        contract_data = {
                                            'first_name': self.request.user.profile.first_name,
                                            'last_name': self.request.user.profile.last_name,
                                            'today': datetime.astimezone(datetime.today()) ,
                                            'address_1': self.request.user.profile.address_1,
                                            'address_2': self.request.user.profile.address_2,
                                            'city': self.request.user.profile.city,
                                            'state': self.request.user.profile.state,
                                            'amount': int(amount),
                                            'period': int(int(new_user_investment.maturity_days)/30),
                                            'plan_name': plan.name,
                                            'plan_percentage': plan.percentage_interest
                                        

                                        }

                                        contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                        new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                                        send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                        send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)


                                    return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))
                        else:
                            if plan.min_investment > int(amount):
                                print("Has to be within min and max")
                                messages.warning(self.request, f"Amount to invest must be more than {plan.min_investment}")
                                return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code':old_inv.txn_code }))
                            else:
                                check_roll = UserInvestmentRollovers.objects.filter(old_investment = old_inv, user =self.request.user.profile)
                                if check_roll.exists():
                                    print('Rollover already exists') 
                                    return HttpResponseRedirect(reverse("investment:dashboard"))
                                else:  
                                    wallet.deposit -= the_diff
                                    wallet.save()
                                    transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                                    new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                                    new_user_investment.save()
                                    if display_name or display_name != None:
                                        new_user_investment.display_name = display_name
                                        new_user_investment.save()
                                    new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                                    new_user_earning.save()
                                    matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                    new_user_investment.maturity_date = matured_at
                                    new_user_investment.is_rollover = True
                                    if plan.category.name == "CIP":
                                        new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                                    elif plan.category.name == "HIP":
                                        new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                    new_user_investment.save()

                                    old_inv.has_been_rolled_over = True
                                    old_inv.save()

                                    new_rollover = UserInvestmentRollovers.objects.create(old_investment=old_inv, new_investment=new_user_investment, user=self.request.user.profile)

                                    new_investment_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")
                                    
                                    new_rollover_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Rollover of {old_inv.txn_code} has been activated")

                                    new_deduction_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Your flex wallet has been debited with a sum of {the_diff}  ")


                                    if plan.category.name == "CIP":
                                        contract_data = {
                                            'first_name': self.request.user.profile.first_name,
                                            'last_name': self.request.user.profile.last_name,
                                            'today': datetime.astimezone(datetime.today()) ,
                                            'address_1': self.request.user.profile.address_1,
                                            'address_2': self.request.user.profile.address_2,
                                            'city': self.request.user.profile.city,
                                            'state': self.request.user.profile.state,
                                            'amount': int(amount),
                                            'period': int(int(new_user_investment.maturity_days)/30),
                                            'plan_name': plan.name,
                                            'plan_percentage': plan.percentage_interest,
                                            'plan_min': int(plan.min_investment),
                                            'plan_max': ''
                                        

                                        }

                                        contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                        new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                                        send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                        send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                                    
                                    elif plan.category.name == "HIP":
                                        contract_data = {
                                            'first_name': self.request.user.profile.first_name,
                                            'last_name': self.request.user.profile.last_name,
                                            'today': datetime.astimezone(datetime.today()) ,
                                            'address_1': self.request.user.profile.address_1,
                                            'address_2': self.request.user.profile.address_2,
                                            'city': self.request.user.profile.city,
                                            'state': self.request.user.profile.state,
                                            'amount': int(amount),
                                            'period': int(int(new_user_investment.maturity_days)/30),
                                            'plan_name': plan.name,
                                            'plan_percentage': plan.percentage_interest
                                        
                                    
                                        }

                                        contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"
                                        new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)
                                        send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                        send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)

                                    return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))
                #check if it was reduced
                elif int(old_inv.amount) > int(amount):
                    the_diff = int(old_inv.amount) - int(amount)
                    print(f"You invested less so ur balance is {the_diff}")

                    if plan.max_investment and plan.max_investment != None:
                        if plan.min_investment > int(amount) or plan.max_investment < int(amount):
                            print("Has to be within min and max")
                            messages.warning(self.request, f"Amount to invest must be between {plan.min_investment} and {plan.max_investment} ")
                            return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code':old_inv.txn_code }))
                        else:
                            check_roll = UserInvestmentRollovers.objects.filter(old_investment = old_inv, user =self.request.user.profile)
                            if check_roll.exists():
                                print('Rollover already exists') 
                                return HttpResponseRedirect(reverse("investment:dashboard"))
                            else:

                                wallet.deposit += the_diff
                                wallet.save()
                                transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                                # maturity_date = datetime.now() + timedelta(int(plan.maturity_period))
                                new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                                new_user_investment.save()
                                if display_name or display_name != None:
                                    new_user_investment.display_name = display_name
                                    new_user_investment.save()
                                new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                                new_user_earning.save()
                                matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.maturity_date = matured_at
                                new_user_investment.is_rollover = True
                                if plan.category.name == "CIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                                elif plan.category.name == "HIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.save()

                                old_inv.has_been_rolled_over = True
                                old_inv.save()

                                new_rollover = UserInvestmentRollovers.objects.create(old_investment=old_inv, new_investment=new_user_investment, user=self.request.user.profile)



                                new_investment_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")

                                new_rollover_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Rollover of {old_inv.txn_code} has been activated")

                                new_refund_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Refund of  {the_diff} has been credited to your flex wallet")

                                
                                

                                if plan.category.name == "CIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest,
                                        'plan_min': int(plan.min_investment),
                                        'plan_max': int(plan.max_investment)                            
                                    }
                                    
                                    contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                    new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code, contract_data)

                                    send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                                
                                elif plan.category.name == "HIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest
                                    

                                    }

                                    contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                    new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                                    send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)

                                return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))

                    else:
                        if plan.min_investment > int(amount):
                            print("Has to be within min and max")
                            messages.warning(self.request, f"Amount to invest must be more than {plan.min_investment}")
                            return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code':old_inv.txn_code }))
                        else:
                            check_roll = UserInvestmentRollovers.objects.filter(old_investment = old_inv, user =self.request.user.profile)
                            if check_roll.exists():
                                print('Rollover already exists') 
                                return HttpResponseRedirect(reverse("investment:dashboard"))
                            else:

                                wallet.deposit += the_diff
                                wallet.save()
                                transaction_code = str(''.join(random.choices(string.digits, k = 13)))
                                new_user_investment = UserInvestment(txn_code = transaction_code, user=self.request.user.profile, amount= int(amount), maturity_days = maturity, plan=plan, active=True)
                                new_user_investment.save()
                                if display_name or display_name != None:
                                    new_user_investment.display_name = display_name
                                    new_user_investment.save()
                                new_user_earning = UserInvestmentEarnings(user=self.request.user.profile,plan=new_user_investment, amount=0, active=True)
                                new_user_earning.save()
                                matured_at = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.maturity_date = matured_at
                                new_user_investment.is_rollover = True
                                if plan.category.name == "CIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(30)
                                elif plan.category.name == "HIP":
                                    new_user_investment.next_payout = new_user_investment.created_at + timedelta(int(new_user_investment.maturity_days))
                                new_user_investment.save()

                                old_inv.has_been_rolled_over = True
                                old_inv.save()

                                new_rollover = UserInvestmentRollovers.objects.create(old_investment=old_inv, new_investment=new_user_investment, user=self.request.user.profile)

                                new_investment_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Investment of {new_user_investment.amount} has been activated")

                                new_rollover_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Rollover of {old_inv.txn_code} has been activated")

                                new_refund_notification = UserNotifications.objects.create(user=self.request.user.profile, message=f"Refund of  {the_diff} has been credited to your flex wallet")


                                


                                if plan.category.name == "CIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest,
                                        'plan_min': int(plan.min_investment),
                                        'plan_max': ''
                                    

                                    }

                                    contract_filename = f"CIP_AGREEMENT_{new_user_investment.txn_code}.pdf"

                                    new_render_to_file('contracts/cip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)

                                    send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)
                                
                                elif plan.category.name == "HIP":
                                    contract_data = {
                                        'first_name': self.request.user.profile.first_name,
                                        'last_name': self.request.user.profile.last_name,
                                        'today': datetime.astimezone(datetime.today()) ,
                                        'address_1': self.request.user.profile.address_1,
                                        'address_2': self.request.user.profile.address_2,
                                        'city': self.request.user.profile.city,
                                        'state': self.request.user.profile.state,
                                        'amount': int(amount),
                                        'period': int(int(new_user_investment.maturity_days)/30),
                                        'plan_name': plan.name,
                                        'plan_percentage': plan.percentage_interest

                                    }

                                    contract_filename = f"HIP_AGREEMENT_{new_user_investment.txn_code}.pdf"
                                    new_render_to_file('contracts/hip_contract.html',contract_filename, new_user_investment.txn_code,  contract_data)
                                    send_investment_started_mail.delay(self.request.user.pk, new_user_investment.pk, contract_filename)
                                    send_investment_started_mail_admin.delay(self.request.user.pk, new_user_investment.pk)

                                return redirect(reverse('investment:investment_successful', kwargs={'plan_id':new_user_investment.pk}))

            else:
                messages.info(self.request, f" You have to agree to Terms and Condition to proceed!")
                return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code': old_inv.txn_code }))


        return HttpResponseRedirect(reverse("investment:process_rollover", kwargs={'plan_id': plan.pk, 'inv_txn_code': old_inv.txn_code }))



@login_required
def investment_successful(request, plan_id):
    template = 'investment/investment_successful.html'
    my_plan = UserInvestment.objects.filter(user=request.user.profile, pk = plan_id).first()
    context = {
        'my_plan':my_plan
    }
    return render(request, template, context)




# MAINTENANCE COMPLETE - 27/02/2021
class PlanDetails(View):
    def get(self, request, plan_id, *args, **kwargs):

        profile = Profile.objects.get(user=self.request.user)

        today = datetime.now().date()
        print(today)

        user_wallet = MainWallet.objects.filter(user=profile).first()
        user_deposit_balance = user_wallet.deposit
        print(user_deposit_balance)

        if not profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')

        if profile.investement_verified == 'pending':
            print("KYC Pending")
            return redirect('investment:kyc-pending')
        elif profile.investement_verified == 'rejected':
            print("KYC Rejected")
            return redirect('investment:kyc-rejected')
    
        my_plan = UserInvestment.objects.filter(user=self.request.user.profile, pk = plan_id).first()
        user_earnings = UserInvestmentEarnings.objects.filter(plan=my_plan).aggregate(amount_sum=Sum("amount"))
        earnings = user_earnings['amount_sum']
        print(earnings)
        inv_earning = UserInvestmentEarnings.objects.filter(plan=my_plan).first()
        print(inv_earning.amount)

        
        
        template = 'investment/plan_details.html'

        context = {
            'profile':profile,
            'current_earning': inv_earning.amount,
            'my_plan': my_plan, 
            'today': today,
            'user_deposit_balance':user_deposit_balance
        } 

        return render(self.request, template, context)
    def post(self, request, plan_id, *args, **kwargs):

        profile = Profile.objects.get(user=self.request.user)

        user_wallet = MainWallet.objects.filter(user=profile).first()
        

        my_plan = UserInvestment.objects.filter(user=profile, pk = plan_id).first()

        amount  = self.request.POST.get('topup_amount')
        print(amount)
        t_and_c  = self.request.POST.get('t_and_c')
        try:
            if t_and_c:
                if int(amount) <= user_wallet.deposit:
                    if int(amount) < 100000:
                        messages.error(self.request, f"The minimum top up amount is N50,000")
                        return HttpResponseRedirect(reverse("investment:plan_details", kwargs={'plan_id': my_plan.pk }))
                    else:
                        past_investments = UserInvestment.objects.filter(user=profile, plan = my_plan.plan, active=True).aggregate(amount_sum=Sum("amount"))
                        has_invested = past_investments['amount_sum']
                        print(f" past investment of user is {has_invested}")
                        if my_plan.plan.max_investment or my_plan.plan.max_investment != None:
                            if has_invested and (has_invested + int(amount)) > my_plan.plan.max_investment:
                                print("caught first error")
                                messages.error(self.request, f"Your Accumulated investment for this plan has exceeded the plan max investment!")
                                return HttpResponseRedirect(reverse("investment:plan_details", kwargs={'plan_id': my_plan.pk }))
                        print("caught second error")
                        user_wallet.deposit -= int(amount)
                        user_wallet.save()
                        old_amount = my_plan.amount
                        my_plan.amount += int(amount)
                        my_plan.save()

                        new_top_up = UserInvestmentTopups.objects.create(investment=my_plan,user=profile,amount=int(amount))

                        if my_plan.plan.category.name == "CIP":
                            contract_data = {
                                'first_name': profile.first_name,
                                'last_name': profile.last_name,
                                'today': datetime.astimezone(datetime.today()) ,
                                'address_1': profile.address_1,
                                'address_2': profile.address_2,
                                'city': profile.city,
                                'state': profile.state,
                                'custom_topup': int(amount),
                                'total_sum_if_topup': int(amount) + int(old_amount),
                                'plan_created': my_plan.created_at
                           
                            }

                            contract_filename = f"TOP_UP_NOTICE_{my_plan.txn_code}.pdf"

                            new_render_to_file_top_up('contracts/cip_topup.html',contract_filename, new_top_up.pk,  contract_data)
                            send_toup_confirmed_mail(self.request.user.pk, amount, my_plan.pk, new_top_up.pk, contract_filename)

                        elif my_plan.plan.category.name == "HIP":
                            contract_data = {
                                'first_name': profile.first_name,
                                'last_name': profile.last_name,
                                'today': datetime.astimezone(datetime.today()) ,
                                'address_1': profile.address_1,
                                'address_2': profile.address_2,
                                'city': profile.city,
                                'state': profile.state,
                                'custom_topup': int(amount),
                                'total_sum_if_topup': int(amount) + int(old_amount),
                                'plan_created': my_plan.created_at
                            }

                            contract_filename = f"TOP_UP_NOTICE_{my_plan.txn_code}.pdf"

                            new_render_to_file_top_up('contracts/hip_topup.html',contract_filename, new_top_up.pk,  contract_data)
                            send_toup_confirmed_mail(self.request.user.pk, amount, my_plan.pk, new_top_up.pk, contract_filename)

                        send_toup_confirmed_mail_admin.delay(self.request.user.pk, amount, my_plan.pk)   
                        return HttpResponseRedirect(reverse("investment:plan_details", kwargs={'plan_id': my_plan.pk }))
                else:
                    print("caught third error")
                    messages.error(self.request, f"The top up amount must be less than your wallet balance")
                    return HttpResponseRedirect(reverse("investment:plan_details", kwargs={'plan_id': my_plan.pk }))
            else:
                messages.error(self.request, f"You have to agree to Terms and Condition to proceed!")
                return HttpResponseRedirect(reverse("investment:plan_details", kwargs={'plan_id': my_plan.pk }))

            

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise


#GET BACK TO THIS 
def cip_investment_contract_render_pdf_view(request, plan_id):
    template_path = 'contracts/cip_contract.html'
    context = {'myvar': 'this is your template context'}
    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=response)
    # if error then show some funy view
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response




# PPP CRONTABS
# def credit_hip_active_investments(request):
#     p = lambda x: x/100
#     today = datetime.now()
#     today = pytz.utc.localize(today)
    
#     print(today)
#     active_investments = UserInvestment.objects.filter(active=True, completed=False, plan__category__name="HIP")
#     if active_investments.exists():
#         for investment in active_investments:
#             amount = investment.amount
#             plan = investment.plan
#             percentage = plan.percentage_interest
#             maturity_date = investment.maturity_date
#             created_date = investment.created_at
#             next_payout = investment.next_payout
#             maturity_days = investment.maturity_days
#             daily_percentage = int(percentage) / maturity_days
#             print(daily_percentage)
#             earning = float(amount) *p(daily_percentage)
#             print(earning)

#             investment_earning = UserInvestmentEarnings.objects.filter(plan=investment, active=True, completed=False)
            
#             for user_earnings in investment_earning:
#                 user_investment_wallet = InvestmentWallet.objects.get(user=user_earnings.user)

#                 if today.date() == maturity_date.date():
#                     user_earnings.amount += Decimal(earning)
#                     user_earnings.save()
#                     print(f"earning of maturity period is {user_earnings.amount} ")
#                     user_investment_wallet.balance += (investment.amount + user_earnings.amount)
#                     user_investment_wallet.save()

#                     user_earnings.amount = 0 
#                     user_earnings.completed = True 
#                     user_earnings.active = False
#                     user_earnings.save()

#                     user_earnings.plan.completed = True
#                     user_earnings.plan.active = False
#                     user_earnings.plan.save()
#                     print(f" first worked for {user_earnings.user.first_name}")

#                     email_profile = user_earnings.user
#                     domain = Site.objects.get_current().domain
#                     subject, from_email, to = 'Good Job!', 'PIPMINDS <dev@scriptdeskng.com>', [
#                         email_profile.user.email]
#                     # text_content = f" Dear {user.username}. Welcome to Ultra "
#                     html_content = render_to_string(
#                         'events/cip_complete_investment.html', {
#                             'first_name': email_profile.first_name,
#                             'last_name':email_profile.last_name,
#                             'investment_name': investment.plan.name,
#                             'investment_category': investment.plan.category.name,
#                             'percentage': investment.plan.percentage_interest,
#                             'capital': investment.amount, 
#                             'wallet_url': f'http://{domain}/wallet/wallets'
                            
#                         })
#                     msg = EmailMessage(subject, html_content, from_email, to)
#                     msg.content_subtype = "html"
#                     msg.send()

#                 else:
#                     user_earnings.amount += Decimal(earning)
#                     user_earnings.save()
#                     print(user_earnings)

#                     print(f" 3rd and normal worked for {user_earnings.user.first_name}")


            
#         #ADD VALUE TO SPONSOR TREE 
#         for profile in active_investments:
#             user = profile.user
#             capital = profile.amount
#             if user.get_user_sponsors:
#                 for fathers in user.get_user_sponsors:
#                     dad = fathers.sponsor
#                     dad_wallet = ReferralWallet.objects.filter(user=dad).first()
#                     earning = float(capital) *p(3)
#                     daily_earning = earning / maturity_days
#                     print(daily_earning)
#                     dad_wallet.balance += Decimal(daily_earning) 
#                     dad_wallet.save()
#                     user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=dad, amount = Decimal(daily_earning) )
#                     user_ref_earning.save()

                        
                    
#                     if fathers.sponsor.get_user_sponsors:
#                         for grand_fathers in fathers.sponsor.get_user_sponsors:
#                             #Add 1% to grand father
#                             grand_dad = grand_fathers.sponsor
#                             grand_dad_wallet = ReferralWallet.objects.filter(user=grand_dad).first()
#                             earning = float(capital) *p(1)
#                             daily_earning = earning / maturity_days
#                             print(daily_earning)
#                             grand_dad_wallet.balance += Decimal(daily_earning) 
#                             grand_dad_wallet.save()
#                             user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=grand_dad, amount = Decimal(daily_earning) )
#                             user_ref_earning.save()
                            

#                             if grand_fathers.sponsor.get_user_sponsors:
#                                 for great_grands in grand_fathers.sponsor.get_user_sponsors:
#                                     great_grand = great_grands.sponsor
#                                     great_grand_wallet = ReferralWallet.objects.filter(user=great_grand).first()
#                                     earning = float(capital) *p(0.75)
#                                     daily_earning = earning / maturity_days
#                                     print(daily_earning)
#                                     great_grand_wallet.balance += Decimal(daily_earning) 
#                                     great_grand_wallet.save()
#                                     user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=great_grand, amount = Decimal(daily_earning))
#                                     user_ref_earning.save()

#     return redirect('investment:dashboard')


# def credit_cip_active_investments(request):
#     p = lambda x: x/100
#     today = datetime.now()
#     today = pytz.utc.localize(today)
    
#     print(today)
#     active_investments = UserInvestment.objects.filter(active=True, completed=False, plan__category__name="CIP")
#     if active_investments.exists():
#         for investment in active_investments:
#             amount = investment.amount
#             plan = investment.plan
#             percentage = plan.percentage_interest
#             maturity_date = investment.maturity_date
#             created_date = investment.created_at
#             next_payout = investment.next_payout
#             daily_percentage = int(percentage) / 30 
#             earning = float(amount) *p(daily_percentage)


#             investment_earning = UserInvestmentEarnings.objects.filter(plan=investment, active=True, completed=False).order_by('-id')
            
#             # for user_earnings in investment_earning:
#             #     user_investment_wallet = InvestmentWallet.objects.filter(user=user_earnings.user).first()

            #     if maturity_date and today.date() == maturity_date.date():

            #         transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
            #         if user_earnings.user.remit_inv_funds_to_wallet:
            #             user_earnings.amount += Decimal(earning)
            #             user_earnings.save()
            #             print(f"earning of maturity period is {user_earnings.amount} ")

            #             new_payment = Payments.objects.create(txn_code=transaction_code, amount=user_earnings.amount, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

            #             new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

            #             new_capital_payment = Payments.objects.create(txn_code=transaction_code, amount=investment.amount, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"CIP CAPITAL Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
                        
            #             new_capital_tnx = Transaction.objects.create(amount=investment.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

            #             # user_investment_wallet.balance += (investment.amount + user_earnings.amount)
            #             total_payout = investment.amount + user_earnings.amount
            #             # user_investment_wallet.save()
            #             user_earnings.plan.profit_earned += earning
            #             user_earnings.plan.profit_paid += user_earnings.amount
            #             #Fix  a bug here 
            #             user_earnings.amount = 0
            #             user_earnings.completed = True 
            #             user_earnings.active = False
            #             user_earnings.save()

            #             user_earnings.plan.completed = True
            #             user_earnings.plan.active = False
            #             user_earnings.plan.save()

            #             new_tnx = Transaction.objects.create(amount=total_payout, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')
                        
                        

            #             # email_profile = user_earnings.user
            #             # domain = 'portal.pipminds.com'
            #             # subject, from_email, to = 'Good Job!', 'PIPMINDS <hello@pipminds.com>', [
            #             #     email_profile.user.email]
            #             # # text_content = f" Dear {user.username}. Welcome to Ultra "
            #             # html_content = render_to_string(
            #             #     'events/cip_complete_investment.html', {
            #             #         'first_name': email_profile.first_name,
            #             #         'last_name':email_profile.last_name,
            #             #         'investment_name': investment.plan.name,
            #             #         'investment_category': investment.plan.category.name,
            #             #         'percentage': investment.plan.percentage_interest,
            #             #         'capital': investment.amount, 
            #             #         'wallet_url': f'http://{domain}/wallet/wallets'
                                
            #             #     })
            #             # msg = EmailMessage(subject, html_content, from_email, to)
            #             # msg.content_subtype = "html"
            #             # msg.send()

            #             print(f" first worked for {user_earnings.user.first_name}")
                    
            #         else:
            #             print("User is to be paid into bank account ")
            #             user_earnings.amount += Decimal(earning)
            #             user_earnings.save()
            #             print(f"earning of maturity period is {user_earnings.amount} ")
            #             total_payout = investment.amount + user_earnings.amount
            #             user_earnings.plan.profit_earned += earning
            #             user_earnings.plan.profit_paid += user_earnings.amount
                        
            #             # new_payment = Payments(txn_code=transaction_code, amount=total_payout, user = user_earnings.user, status='pending',remark=f"CIP CAPITAL AND ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
            #             # new_payment.save()

            #             new_payment = Payments.objects.create(txn_code=transaction_code, amount=user_earnings.amount, user = user_earnings.user, destination="bank_account", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

            #             new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

            #             new_capital_payment = Payments.objects.create(txn_code=transaction_code, amount=investment.amount, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"CIP CAPITAL Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
                        
            #             new_capital_tnx = Transaction.objects.create(amount=investment.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

            #             user_earnings.amount = 0
            #             user_earnings.completed = True 
            #             user_earnings.active = False
            #             user_earnings.save()

            #             user_earnings.plan.completed = True
            #             user_earnings.plan.active = False
            #             user_earnings.plan.save()

            #             new_tnx = Transaction.objects.create(amount=total_payout, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')
                     

            #             #SEND EMAIL TO ADMIN AND USER HERE 


            #     elif next_payout and today.date() == next_payout.date():
            #         transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))

            #         if user_earnings.user.remit_inv_funds_to_wallet:
            #             # user_investment_wallet.balance += user_earnings.amount
            #             payout_this_month = user_earnings.amount

            #             new_payment = Payments.objects.create(txn_code=transaction_code, amount=payout_this_month, user = user_earnings.user, destination="investment_wallet", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

            #             new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

            #             # user_investment_wallet.save()
            #             user_earnings.plan.profit_earned += earning
            #             user_earnings.plan.profit_paid += payout_this_month
            #             user_earnings.amount = earning
            #             user_earnings.save()

            #             user_earnings.plan.next_payout = today + timedelta(30)
            #             user_earnings.plan.save()

            #             # new_tnx = Transaction(amount=payout_this_month, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')
            #             # new_tnx.save()
                        

            #             #SEND EMAIL HERE 
                        
            #             # email_profile = user_earnings.user
            #             # domain = 'portal.pipminds.com'
            #             # subject, from_email, to = 'Hurray! Its PayDay', 'PIPMINDS <hello@pipminds.com>', [
            #             #     email_profile.user.email]
            #             # # text_content = f" Dear {user.username}. Welcome to Ultra "
            #             # html_content = render_to_string(
            #             #     'events/cip_monthly_interest.html', {
            #             #         'first_name': email_profile.first_name,
            #             #         'last_name':email_profile.last_name,
            #             #         'investment_name': investment.plan.name,
            #             #         'investment_category': investment.plan.category.name,
            #             #         'percentage': investment.plan.percentage_interest,
            #             #         'payout_this_month': payout_this_month, 
            #             #         'wallet_url': f'http://{domain}/wallet/wallets'
                                
            #             #     })
            #             # msg = EmailMessage(subject, html_content, from_email, to)
            #             # msg.content_subtype = "html"
            #             # msg.send()
            #         else:
            #             print("User is to be paid into their bank account")
            #             payout_this_month = user_earnings.amount

            #             new_payment = Payments.objects.create(txn_code=transaction_code, amount=payout_this_month, user = user_earnings.user, destination="bank_account", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

            #             new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

            #             user_earnings.plan.profit_earned += earning
            #             user_earnings.plan.profit_paid += payout_this_month

            #             # new_payment = Payments(txn_code=transaction_code, amount=payout_this_month, user = user_earnings.user, status='pending',remark=f"ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")
            #             # new_payment.save()

            #             # new_tnx = Transaction(amount=payout_this_month, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')
            #             # new_tnx.save()

            #             user_earnings.amount = earning
            #             user_earnings.save()
            #             user_earnings.plan.next_payout = today + timedelta(30)
            #             user_earnings.plan.save()

            #             #SEND A MAIL TO ADMIN AND USER HERE 
                        


            #         print(f" second worked for {user_earnings.user.first_name}")

            #     else:
            #         user_earnings.amount += Decimal(earning)
            #         user_earnings.save()
            #         user_earnings.plan.profit_earned += earning
            #         user_earnings.plan.save()
            #         print(user_earnings)

            #         print(f" 3rd and normal worked for {user_earnings.user.first_name}")


            
    #     #ADD VALUE TO SPONSOR TREE 
    #     for profile in active_investments:
    #         user = profile.user
    #         capital = profile.amount
    #         if user.get_user_sponsors:
    #             for fathers in user.get_user_sponsors:
    #                 dad = fathers.sponsor
    #                 dad_wallet = ReferralWallet.objects.filter(user=dad).first()
    #                 earning = float(capital) *p(2)
    #                 daily_earning = earning / 30
    #                 # print(daily_earning)
               
    #                 if dad.ppp_verfied: 
    #                     if dad.user.user_membership.user_subscription.exists():
    #                         print(f"subscription status of dad is  {dad.user.user_membership.user_subscription.first().active}")
    #                         if dad.user.user_membership.user_subscription.first().active == True:
    #                             if dad.has_active_investment and dad.has_active_investment_sum >= 300000:
    #                                 dad_wallet.balance += Decimal(daily_earning) 
    #                                 dad_wallet.save()
    #                                 user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=dad, amount = Decimal(daily_earning) )
    #                                 user_ref_earning.save()
    #                                 new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = dad, txn_method="manual", txn_type='referral_earnings')
    #                                 new_tnx.save()

    #                     elif dad.pioneer_ppp_member == True:
    #                         print(f"dad {dad} is a pioneer ")
    #                         if dad.has_active_investment and dad.has_active_investment_sum >= 300000:
    #                             dad_wallet.balance += Decimal(daily_earning) 
    #                             dad_wallet.save()
    #                             user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=dad, amount = Decimal(daily_earning) )
    #                             user_ref_earning.save()
    #                             new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = dad, txn_method="manual", txn_type='referral_earnings')
    #                             new_tnx.save()


                        
                    
    #                 if fathers.sponsor.get_user_sponsors:
    #                     for grand_fathers in fathers.sponsor.get_user_sponsors:
    #                         #Add 1% to grand father
    #                         grand_dad = grand_fathers.sponsor
    #                         grand_dad_wallet = ReferralWallet.objects.filter(user=grand_dad).first()
    #                         earning = float(capital) *p(1)
    #                         daily_earning = earning / 30
    #                         # print(daily_earning)
                           
    #                         if grand_dad.ppp_verfied:
    #                             if grand_dad.user.user_membership.user_subscription.exists():
    #                                 print(f"subscription status of grandad is  {grand_dad.user.user_membership.user_subscription.first().active}")
    #                                 if grand_dad.user.user_membership.user_subscription.first().active == True:
    #                                     if grand_dad.has_active_investment and grand_dad.has_active_investment_sum >= 300000:
    #                                         grand_dad_wallet.balance += Decimal(daily_earning) 
    #                                         grand_dad_wallet.save()
    #                                         user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=grand_dad, amount = Decimal(daily_earning) )
    #                                         user_ref_earning.save()
    #                                         new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = grand_dad, txn_method="manual", txn_type='referral_earnings')
    #                                         new_tnx.save()

    #                             elif grand_dad.pioneer_ppp_member == True:
    #                                 print(f"grandad {grand_dad} is a pioneer ")
    #                                 if grand_dad.has_active_investment and grand_dad.has_active_investment_sum >= 300000:
    #                                     grand_dad_wallet.balance += Decimal(daily_earning) 
    #                                     grand_dad_wallet.save()
    #                                     user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=grand_dad, amount = Decimal(daily_earning) )
    #                                     user_ref_earning.save()
    #                                     new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = grand_dad, txn_method="manual", txn_type='referral_earnings')
    #                                     new_tnx.save()
                                        
                            

    #                         if grand_fathers.sponsor.get_user_sponsors:
    #                             for great_grands in grand_fathers.sponsor.get_user_sponsors:
    #                                 great_grand = great_grands.sponsor
    #                                 great_grand_wallet = ReferralWallet.objects.filter(user=great_grand).first()
    #                                 earning = float(capital) *p(0.5)
    #                                 daily_earning = earning / 30
    #                                 # print(daily_earning)
    #                                 if great_grand.ppp_verfied:
    #                                     if great_grand.user.user_membership.user_subscription.exists():
    #                                         print(f"subscription status of great_grand is  {great_grand.user.user_membership.user_subscription.first().active}")
    #                                         if great_grand.user.user_membership.user_subscription.first().active == True:
    #                                             if great_grand.has_active_investment and great_grand.has_active_investment_sum >= 300000:
    #                                                 great_grand_wallet.balance += Decimal(daily_earning) 
    #                                                 great_grand_wallet.save()
    #                                                 user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=great_grand, amount = Decimal(daily_earning))
    #                                                 user_ref_earning.save()
    #                                                 new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = great_grand, txn_method="manual", txn_type='referral_earnings')
    #                                                 new_tnx.save()
    #                                     elif great_grand.pioneer_ppp_member == True:
    #                                         print(f"great_grand {great_grand} is a pioneer ")
    #                                         if great_grand.has_active_investment and great_grand.has_active_investment_sum >= 300000:
    #                                             great_grand_wallet.balance += Decimal(daily_earning) 
    #                                             great_grand_wallet.save()
    #                                             user_ref_earning = UserReferralEarnings(txn_code=str(''.join(random.choices(string.digits, k = 13))), user=great_grand, amount = Decimal(daily_earning))
    #                                             user_ref_earning.save()
    #                                             new_tnx = Transaction(amount=user_ref_earning.amount, txn_code=user_ref_earning.txn_code, user = great_grand, txn_method="manual", txn_type='referral_earnings')
    #                                             new_tnx.save()
    # return redirect('investment:dashboard')









# #REWORK THIS 
# def complete_inv_cycle(request):
#     active_investments = UserInvestment.objects.filter(active=True, completed=False)
#     today = datetime.now()
#     today = pytz.utc.localize(today)
#     if active_investments.exists():
#         for investment in active_investments:
#             amount = investment.amount
#             plan = investment.plan
#             percentage = plan.percentage_interest
#             maturity_date = investment.maturity_date

#             investement_earning = UserInvestmentEarnings.objects.filter(plan=investment).first()
#             print(investement_earning)

#             if maturity_date and today >= maturity_date:
#                 print("Investment complete")
#                 investment.completed = True
#                 investment.active = False 
#                 investment.save()

#                 if investement_earning:
#                     investement_earning.completed = True
#                     investement_earning.active = False
#                     investement_earning.save()





#             print(today)
#             print(investment.maturity_date)


#     return redirect('investment:dashboard')




# class GeneratePdf(View):
#     def get(self, request, *args, **kwargs):
#         data = {
#             #  'today': datetime.date.today(), 
#             #  'amount': 39.99,
#             # 'customer_name': 'Cooper Mann',
#             # 'order_id': 1233434,
#         }
#         pdf = render_to_pdf('contracts/test_contract.html', data)
#         return HttpResponse(pdf, content_type='application/pdf')



# def send_inv_mature_reminder(request):

#     today = datetime.astimezone(datetime.today())
    
#     print(today)
#     active_investments = UserInvestment.objects.filter(active=True, completed=False)
#     if active_investments.exists():
#         for inv in active_investments:
#             if datetime.date(today) == (datetime.date(inv.maturity_date) - timedelta(days=7)):
#                 print("Today is 7 days to expiry date")
#                 print(f"{inv.user.user.email}")
#                 print(f"today is {datetime.date(today)} and inv will expire  {datetime.date(inv.maturity_date)}")
                
#                 email_profile = inv.user
                
#                 subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
#                     email_profile.user.email]

#                 html_content = render_to_string(
#                     'events/inv_mature_at_7days.html', {
#                         'email': email_profile.user.email,
#                         'first_name': email_profile.first_name,
#                         'last_name':email_profile.last_name,
#                         'investment_display_name': inv.display_name,
#                         'investment_txn_code': inv.txn_code,
#                         'investment_amount': inv.amount,
#                         'inv_maturity_datetime': inv.maturity_date,
#                         'inv_maturity_cat': inv.plan.category.name,
#                         'period': int(inv.maturity_days), 
#                         'inv_maturity_date': datetime.date(inv.maturity_date),
#                         'rollover_starts': f"{(inv.maturity_date + timedelta(days=1)).date()}",
#                         'rollover_ends': f"{(inv.maturity_date + timedelta(days=8)).date()}"
#                     })
#                 msg = EmailMessage(subject, html_content, from_email, to)
#                 msg.content_subtype = "html"
#                 msg.send()
#             elif datetime.date(today) == (datetime.date(inv.maturity_date) - timedelta(days=3)):
#                 print("Today is 3 days to expiry date")
#                 print(f"{inv.user.user.email}")
             
#                 print(f"today is {datetime.date(today)} and inv will expire  {datetime.date(inv.maturity_date)}")
#                 email_profile = inv.user
             
#                 subject, from_email, to = 'NOTICE OF INVESTMENT MATURITY!', 'PIPMINDS <hello@pipminds.com>', [
#                     email_profile.user.email]

#                 html_content = render_to_string(
#                     'events/inv_mature_at_3days.html', {
#                         'email': email_profile.user.email,
#                         'first_name': email_profile.first_name,
#                         'last_name':email_profile.last_name,
#                         'investment_display_name': inv.display_name,
#                         'investment_txn_code': inv.txn_code,
#                         'investment_amount': inv.amount,
#                         'inv_maturity_datetime': inv.maturity_date,
#                         'inv_maturity_cat': inv.plan.category.name,
#                         'period': int(inv.maturity_days), 
#                         'inv_maturity_date': datetime.date(inv.maturity_date),
#                         'rollover_starts': f"{(inv.maturity_date + timedelta(days=1)).date()}",
#                         'rollover_ends': f"{(inv.maturity_date + timedelta(days=8)).date()}"
#                     })
#                 msg = EmailMessage(subject, html_content, from_email, to)
#                 msg.content_subtype = "html"
#                 msg.send()

#     return redirect('investment:dashboard')

# def generate_payment_for_completed_inv(request):

#     today = datetime.astimezone(datetime.today())
    
#     print(today)
#     active_investments = UserInvestment.objects.filter(active=False, completed=True)
#     if active_investments.exists():
#         for inv in active_investments:
#             if datetime.date(today) > inv.get_rollover_ends:
#                 print(inv.user.user.email)
#                 print(inv.get_rollover_ends)
#                 print(f"Generate payment for {inv.user.user.email} ")

#                 if inv.plan.category.name == 'CIP':
                    
#                     transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
#                     new_capital_payback_get = CapitalPaybacks.objects.filter(user=inv.user, investment=inv).first()
#                     if not new_capital_payback_get:
#                         new_capital_payback = CapitalPaybacks.objects.create(user=inv.user, investment=inv)
#                         new_capital_payback_payment = Payments.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, remark="CIP Capital Payback")
#                         new_capital_payback_transaction = Transaction.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, txn_method='manual' ,txn_type='investment_earnings')
#                 elif inv.plan.category.name == 'HIP':
#                     transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
#                     new_capital_payback_get = CapitalPaybacks.objects.filter(user=inv.user, investment=inv).first()
#                     if not new_capital_payback_get:
#                         new_capital_payback = CapitalPaybacks.objects.create(user=inv.user, investment=inv)
#                         new_capital_payback_payment = Payments.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, remark="HIP Capital Payback")
#                         new_capital_payback_transaction = Transaction.objects.create(txn_code=transaction_code, user=inv.user, amount=inv.amount, txn_method='manual' ,txn_type='investment_earnings')

#     return redirect('investment:dashboard')






