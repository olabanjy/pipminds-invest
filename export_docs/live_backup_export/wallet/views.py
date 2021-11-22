from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, reverse, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.encoding import force_bytes
from django.db.models import Sum
import random, string
from datetime import timedelta, date, datetime, time
from dateutil.parser import parse
from django.utils.timezone import make_aware
import pytz
import requests
import base64
import hashlib
import json

paystack_secret_key = settings.PAYSTACK_SECRET_KEY

monnify_secret_key = settings.MONNIFY_SECRET_KEY
monnify_api_key = settings.MONNIFY_API_KEY
monnify_base_url = settings.MONNIFY_BASE_URL

test_monnify_secret_key = settings.TEST_MONNIFY_SECRET_KEY
test_monnify_api_key = settings.TEST_MONNIFY_API_KEY
test_monnify_base_url = settings.TEST_MONNIFY_BASE_URL


from django.contrib.humanize.templatetags.humanize import naturalday, naturaltime

from .models import *
from .forms import * 
from .tasks import *

from users.models import *
from investment.models import *



class Dashboard(View):
    def get(self, request,  *args, **kwargs):
        if not self.request.user.profile.profile_set_up:
            return redirect('users:profile-set-up')

        if not self.request.user.profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')

        template = 'wallet/index.html'
        wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
        withdraws = Withdrawal.objects.filter(user = self.request.user.profile).order_by('-id').all()
        deposits = Deposit.objects.filter(user = self.request.user.profile).order_by('-id').all()
        investment_wallet = InvestmentWallet.objects.filter(user=self.request.user.profile).first()
        referral_wallet = ReferralWallet.objects.filter(user=self.request.user.profile).first()
        last_withdraw = Withdrawal.objects.filter(user=self.request.user.profile).last()
        

        
        trans = None
        deposit_trans = None
        withdrawal_trans = None
        print(wallet.overall_balance)
        print(type(wallet.overall_balance))
        print(type(investment_wallet.balance))
        print(type(referral_wallet.balance))
        portfolio = int(wallet.overall_balance) + investment_wallet.balance + referral_wallet.balance
 


        if deposits:
            deposit_trans = deposits[:5]
        if withdraws:
            withdrawal_trans =withdraws[:5]


        
       

        context= {
            'wallet':wallet, 
            'investment_wallet': investment_wallet,
            'referral_wallet': referral_wallet,
           
            'portfolio': portfolio, 
            'deposit_trans': deposit_trans,
            'withdrawal_trans' : withdrawal_trans
           
           
        }

        return render(self.request, template, context)

class DepositFunds(View):
    def get(self, request, *args, **kwargs):

        template = 'wallet/deposit.html'
        form = DepositForm()
        context = {
            'form': form,
        }

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):
        form = DepositForm(self.request.POST or None)
        try:
            if form.is_valid():
                amount  = form.cleaned_data.get('amount')
                
                print(amount)

                # if int(amount) < 50000 :
                #     messages.error(self.request, "Minimum deposit is 50,000 NGN")
                #     return HttpResponseRedirect(reverse('wallet:deposit'))
                
                txn_type = form.cleaned_data.get('txn_type')
                print(txn_type)
                if txn_type == '0':
                    print("Scope working, tnx_type 0 ")

                    messages.error(self.request, "Paypal payment gateway not available at the moment, kindly use other options")
                    return HttpResponseRedirect(reverse('wallet:deposit'))

                elif txn_type == '1':
                    print("Scope working, tnx_type 1 ")

                    transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                    
                    new_tnx = Transaction(amount=amount, txn_code=transaction_code, user = self.request.user.profile, txn_method="paystack", txn_type='deposit')
                    new_tnx.save()

                    #initiated_card_deposit.delay(self.request.user.pk, new_tnx.txn_code)

                    return redirect(reverse('wallet:paystack-payment',  kwargs={'transaction_code' : new_tnx.txn_code}))

                elif txn_type == '2':
                    print("Scope working, tnx_type 2 ")
                    print("Got to scope")

                    last_deposit_trans = Transaction.objects.filter(user=self.request.user.profile, txn_method="manual", txn_type='deposit')
                    print("Got here 1")
                    if last_deposit_trans.exists():
                        print("last deposit exist, moving on")
                        last_deposit = last_deposit_trans.last()
                        print(last_deposit)
                        if (make_aware(datetime.now()) - last_deposit.created_at).days < 1:
                            print("Your last deposit was less than a day ago")
                            messages.error(self.request, f"Your last manual deposit was made less than 24hours ago. Please try again by {naturaltime(last_deposit.created_at + timedelta(hours=24))}")
                            return HttpResponseRedirect(reverse('wallet:deposit'))
                        else:
                            print("go ahed and proceed")
                            print("Got here 3")
                            if int(amount) <= 10000000:
                                transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                                
                                new_tnx = Transaction(amount=amount, txn_code=transaction_code, user = self.request.user.profile, txn_method="manual", txn_type='deposit')
                                new_tnx.save()

                                new_deposit = Deposit(txn_code = new_tnx.txn_code,
                                                    user = self.request.user.profile,
                                                    amount = amount, wallet="main", approved=False, status='awaiting_proof'
                                                    )
                                new_deposit.save()

                                

                                return redirect(reverse('wallet:get-ref-code',  kwargs={'txn_code' : new_tnx.txn_code}))

                            else:
                                print("You cannot pay more than do more than 10m in a day")
                                messages.error(self.request, f"You have exceeded the maximum limit of NGN10,000,000 per transaction. Please input a lesser amount!")
                                return HttpResponseRedirect(reverse('wallet:deposit')) 
                            


                    else:
                        print("Got here 2")
                        if int(amount) <= 10000000:
                            transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                            
                            new_tnx = Transaction(amount=amount, txn_code=transaction_code, user = self.request.user.profile, txn_method="manual", txn_type='deposit')
                            new_tnx.save()

                            new_deposit = Deposit(txn_code = new_tnx.txn_code,
                                                user = self.request.user.profile,
                                                amount = amount, wallet="main", approved=False, status='awaiting_proof'
                                                )
                            new_deposit.save()

                            # initiated_manual_deposit.delay(self.request.user.pk, new_tnx.txn_code)
                            #SEND EMAIL TO ADMIN HERE 

                            return redirect(reverse('wallet:get-ref-code',  kwargs={'txn_code' : new_tnx.txn_code}))

                        else:
                            print("You cannot pay more than do more than 10m in a day")
                            messages.error(self.request, f"You have exceeded the maximum limit of NGN10,000,000 per transaction. Please input a lesser amount!")
                            return HttpResponseRedirect(reverse('wallet:deposit')) 

                elif txn_type == '3':
                    print("Scope working, tnx_type 3 ")

                    transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                    
                    new_tnx = Transaction(amount=amount, txn_code=transaction_code, user = self.request.user.profile, txn_method="monnify", txn_type='deposit')
                    new_tnx.save()

                    #initiated_card_deposit.delay(self.request.user.pk, new_tnx.txn_code)

                    return redirect(reverse('wallet:monify-payment',  kwargs={'transaction_code' : new_tnx.txn_code}))    

            # else:
            #     print("Form is not valid")
            #     print(form.errors)
            #     messages.error(self.request, f"{form.errors}")
            #     return HttpResponseRedirect(reverse('wallet:deposit'))

            return HttpResponseRedirect(reverse('wallet:deposit'))

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
            # messages.error(self.request, f"{err_msg}")

            # return HttpResponseRedirect(reverse('wallet:deposit'))
        except:
            print("Unexpected Error")
            # messages.error(self.request, f"Unexpected error! Please try again")
            # return HttpResponseRedirect(reverse('wallet:deposit'))

 
class PaystackPayment(View):
    def get(self, request, transaction_code,  *args, **kwargs):
        transaction = Transaction.objects.filter(txn_code = transaction_code).first()
        template = 'wallet/pay_paystack.html'

        if transaction.approved == True:
            return redirect('wallet:dashboard')
        
        transaction_amount = int(transaction.amount)
        
        context = {
            'transaction': transaction,
            'transaction_amount':transaction_amount
        }
    

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):

        reference = self.request.POST.get('paystackToken')
        transaction_code = self.request.POST.get('transaction_code')
        transaction = Transaction.objects.filter(txn_code=transaction_code).first()
        wallet = MainWallet.objects.get(user = self.request.user.profile)

        headers = {'Authorization': f'Bearer {paystack_secret_key}'}
        resp = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
        response = resp.json()
        try:
            status = response['data']['status']
            auth_code = response['data']['authorization']['authorization_code']
            if status == "success":
                transaction.approved = True
                transaction.save()
                
                wallet.deposit += transaction.amount
                wallet.save()

                new_deposit = Deposit(txn_code = transaction.txn_code,
                                        user = self.request.user.profile,
                                        amount = transaction.amount, status='approved', wallet="main", approved=True
                                        )
                new_deposit.save()
                successful_card_deposit.delay(self.request.user.pk, transaction.txn_code)
                

                messages.success(self.request, 'Payment is successful')
                return redirect(reverse('wallet:payment-success-paystack',kwargs={
                    'txn_code': transaction.txn_code
                }))
            else:
                messages.warning(self.request, 'Payment failed')
                return HttpResponseRedirect(reverse('wallet:deposit'))

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise



@login_required
def update_monnify_transRef(request):
    data = {}
    transRef = request.GET.get('transRef', None)
    trans_code = request.GET.get('trans_code', None)
    print(transRef)
    the_transaction = Transaction.objects.get(txn_code=trans_code)
    if the_transaction:
        update_monnify_transaction_ref.delay(the_transaction.txn_code, transRef)
        print("The transaction reference has been sent to celery to save")
        data.update({'status':True})
    else:
        data.update({'status':False})
    
    return JsonResponse(data)


class MonifyPayment(View):
    def get(self, request, transaction_code,  *args, **kwargs):
        transaction = Transaction.objects.filter(txn_code = transaction_code).first()
        template = 'wallet/pay_monify.html'

        if transaction.approved == True:
            return redirect('wallet:dashboard')
        
        
        transaction_amount = int(transaction.amount)
        
        context = {
            'transaction': transaction,
            'transaction_amount':transaction_amount
        }
    

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):

        reference = self.request.POST.get('monifyToken')
        transaction_code = self.request.POST.get('transaction_code')
        transaction = Transaction.objects.filter(txn_code=transaction_code).first()
        wallet = MainWallet.objects.get(user = self.request.user.profile)
        auth_string = f"{monnify_api_key}:{monnify_secret_key}"
        auth_string_bytes = auth_string.encode("ascii") 
        encoded = base64.b64encode(auth_string_bytes)
        print(encoded)
        encoded_raw = encoded.decode('ascii')
        print(encoded_raw)
        get_basic_headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Basic {encoded_raw}"
                }
        get_basic = requests.post(f"{monnify_base_url}/api/v1/auth/login", headers=get_basic_headers)


        get_basic_auth_response = get_basic.json()
        print(get_basic_auth_response)

        accessToken = get_basic_auth_response['responseBody']['accessToken']

        headers = {'Authorization': f'Bearer {accessToken}'}
        resp = requests.get(
            f"{monnify_base_url}/api/v2/transactions/{reference}", headers=headers)
        response = resp.json()
        print(response)
        try:
            status = response['responseMessage']
            if status == "success":
                monnify_trans_ref = response['responseBody']['transactionReference']
                payment_status = response['responseBody']['paymentStatus']
                payment_reference = response['responseBody']['paymentReference'] 
                if payment_status == "PAID":
                    transaction.approved = True
                    transaction.trans_ref = monnify_trans_ref
                    transaction.save()
                    
                    

                    get_deposit = Deposit.objects.filter(txn_code = payment_reference, user=self.request.user.profile ).first()

                    if get_deposit and get_deposit.approved == True:
                        pass
                    else:
                        new_deposit = Deposit(txn_code = transaction.txn_code,
                                                user = self.request.user.profile,
                                                amount = transaction.amount, status='approved', wallet="main", approved=True, trans_ref = monnify_trans_ref
                                                )
                        new_deposit.save()

                        wallet.deposit += transaction.amount
                        wallet.save()
                        
                    #successful_card_deposit.delay(self.request.user.pk, transaction.txn_code)
                    

                    messages.success(self.request, 'Payment is successful')
                    return redirect(reverse('wallet:payment-success-monnify', kwargs={
                        'txn_code': transaction.txn_code
                    }))
                else:
                    messages.error(self.request, 'Payment failed')
                    return HttpResponseRedirect(reverse('wallet:deposit'))
                
                        
            else:
                messages.error(self.request, 'Payment failed')
                return HttpResponseRedirect(reverse('wallet:deposit'))

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise




def get_manual_trans_code(request, txn_code):
    transaction = Transaction.objects.filter(txn_code=txn_code).first()
    template = 'wallet/get_reference.html'
    context = {
        'transaction': transaction
    }
    return render(request, template, context)
    

class BankTransferPayment(View):
    def get(self, request, transaction_code,  *args, **kwargs):
        transaction = Transaction.objects.filter(txn_code = transaction_code).first()
        template = 'wallet/pay_manual.html'
        form = DepositProofForm()
        print(transaction.get_timeout_time)
        timeout = transaction.get_timeout_time
        for_js = timeout.isoformat()
        print(for_js)
        
        context = {
            'transaction': transaction, 
            'js_timeout': for_js
        }

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):
        transaction_code = self.request.POST.get('the_trans_code')
        print(transaction_code)

        form  = DepositProofForm(self.request.POST, self.request.FILES or None)
        try:
            if form.is_valid():
                proof_file = form.cleaned_data.get('proof_file')
                

                if proof_file:
                    the_deposit = Deposit.objects.get(txn_code=transaction_code)
                    print(the_deposit.amount)

                    the_deposit.proof_of_payment = proof_file
                    the_deposit.status = 'pending'
                    the_deposit.save()

                    return redirect(reverse('wallet:payment-success', kwargs={
                        'txn_code':transaction_code
                    }))
            else:
                print(form.errors)
                messages.error(self.request, f"Please upload the proof of payment to proceed")
                return redirect(reverse('wallet:manual-payment', kwargs={
                    'transaction_code': transaction_code
                }))

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise


        


@login_required
def payment_successful(request, txn_code):

    transaction = Transaction.objects.filter(txn_code = txn_code).first()
    if transaction:
        transaction.approved = True
        transaction.save()
        initiated_manual_deposit.delay(request.user.pk, transaction.txn_code)
        

    context = {
        'txn_code': transaction.txn_code,
        'amount': transaction.amount
    }

    template = 'wallet/payment_successful.html'

    return render(request, template, context)


@login_required
def payment_successful_paystack(request, txn_code):

    transaction = Transaction.objects.filter(txn_code = txn_code).first()
    if transaction:
        transaction.approved = True
        transaction.save()
    

    context = {
        'txn_code': transaction.txn_code,
        'amount': transaction.amount
    }

    template = 'wallet/payment_successful_paystack.html'

    return render(request, template, context)
 
@login_required
def payment_successful_monnify(request, txn_code):

    transaction = Transaction.objects.filter(txn_code = txn_code).first()
    if transaction:
        transaction.approved = True
        transaction.save()
        #successful_monnify_deposit.delay(request.user.pk, transaction.txn_code)
    

    context = {
        'txn_code': transaction.txn_code,
        'amount': transaction.amount
    }

    template = 'wallet/payment_successful_monnify.html'

    return render(request, template, context)

@login_required
def cancel_deposit(request, transaction_code):
    transaction = Transaction.objects.filter(txn_code=transaction_code).first()
    if transaction:
       
        the_deposit = Deposit.objects.filter(txn_code=transaction.txn_code).first()
        if the_deposit:
            the_deposit.delete()
        transaction.delete()
        return redirect('wallet:dashboard')   
    else:
        messages.info(request, "The transaction does not exist")
        return redirect('wallet:dashboard')
    


class WalletsView(View):
    def get(self, request, *args, **kwargs):

        if not self.request.user.profile.profile_set_up:
            return redirect('users:profile-set-up')

        if not self.request.user.profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
      
        ref_can_withdraw = True
        flex_can_withdraw = True
        flex_next_withdrawal = None
        

        flex_wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
        investment_wallet = InvestmentWallet.objects.filter(user=self.request.user.profile).first()
        referral_wallet = ReferralWallet.objects.filter(user=self.request.user.profile).first()

        
        today = datetime.now()
        if not today.day ==1:
            ref_can_withdraw = False

        last_flex_withdrawal = Withdrawal.objects.filter(user=self.request.user.profile, wallet="main")
        print("Got here withdrawal 1")
        if last_flex_withdrawal.exists():
            print("last deposit exist, moving on")
            last_with = last_flex_withdrawal.last()
            print(last_with)
            if (make_aware(datetime.now()) - last_with.created_at).days < 7:
                flex_can_withdraw = False 
                flex_next_withdrawal = naturaltime(last_with.created_at + timedelta(days=7))


        
        template = 'wallet/wallets.html'
        context = {
            'flex_wallet': flex_wallet,
            'investment_wallet': investment_wallet,
            'referral_wallet' : referral_wallet, 
            'ref_can_withdraw': ref_can_withdraw,
            'flex_can_withdraw':flex_can_withdraw,
            'flex_next_withdrawal': flex_next_withdrawal

        }

        return render(self.request, template, context) 



class RequestWithdrawal(View):

    def get(self, request,  *args, **kwargs):

        print(self.kwargs['wallet'])

        wallet = None
        user_bank_account= None

        if self.kwargs['wallet'] == 'investment':
            wallet = InvestmentWallet.objects.filter(user=self.request.user.profile).first()
        elif self.kwargs['wallet'] == 'referral':
            wallet = ReferralWallet.objects.filter(user=self.request.user.profile).first()
        elif self.kwargs['wallet'] == 'flex_wallet':
            wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
        
        

        if not self.request.user.profile.investement_verified:
            return redirect('investment:update-kyc')
        
        if self.request.user.profile.user_bank_account.exists():
            bnk_accout = self.request.user.profile.user_bank_account.first()
            if bnk_accout.account_number == None or bnk_accout.account_name == None or bnk_accout.bank_name == None:
                print("Sorry, it seems your bank account details in incomplete. Please contact admin now to rectify!")
                print(bnk_accout.account_number)
                print(bnk_accout.account_name)
                print(bnk_accout.bank_name)
                messages.error(self.request, f"Sorry,it seems your bank account details in incomplete.. Please contact admin now to rectify!")
                return redirect('wallet:wallets')
            else:
                user_bank_account = bnk_accout
            print(self.request.user.profile.user_bank_account.first())
        else:
            print("Sorry, we don't seem to have your bank account records. Please contact admin now to rectify!")
            messages.error(self.request, f"Sorry, we don't seem to have your bank account records. Please contact admin now to rectify!")
            return redirect('wallet:wallets')
        
        

                
            
        template = 'wallet/withdraw.html'
        form = WithdrawalForm()
        context = {
            'form': form,
            'which_wallet': self.kwargs['wallet'],
            'user_bank_account':user_bank_account
        }

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):
        form = WithdrawalForm(self.request.POST or None)
        flex_wallet = MainWallet.objects.get(user = self.request.user.profile)
        try:
            if form.is_valid():
                amount  = form.cleaned_data.get('amount')
                destination  = form.cleaned_data.get('destination')
                transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))
                
                if self.kwargs['wallet'] == 'investment':
                    if destination == 'bank':
                        wallet = InvestmentWallet.objects.get(user=self.request.user.profile)
                        if int(amount) <= wallet.balance:
                            new_withdrawal = Withdrawal(txn_code = transaction_code, user= self.request.user.profile, amount= amount, wallet='investments')
                            new_withdrawal.save()

                            new_tnx = Transaction(amount=amount, txn_code=new_withdrawal.txn_code, user = self.request.user.profile, txn_method="manual", txn_type='investment_earnings')
                            new_tnx.save()
                        
                            wallet.balance -= amount
                            wallet.save()
                        
                            investment_profit_withrawal_request.delay(self.request.user.pk, new_withdrawal.txn_code)

                            new_notification = UserNotifications(user=self.request.user.profile, message=f"Your withrawal request of  {new_withdrawal.amount} has been received ")
                            new_notification.save()

                            return redirect(reverse('wallet:withdrawal-request-sent',  kwargs={'transaction_code' : new_withdrawal.txn_code}))
                        else:
                            print("Your balance is less than the requested amount")
                            messages.error(self.request, f"Your balance is less than the requested amount, Please choose a lesser amount")
                            return HttpResponseRedirect(reverse('wallet:withdraw', kwargs={'wallet':self.kwargs['wallet']}))

                        
                    elif destination == 'flex_wallet':
                        wallet = InvestmentWallet.objects.get(user=self.request.user.profile)
                        if int(amount) <= wallet.balance:
                            new_withdrawal = Withdrawal(txn_code = transaction_code, user= self.request.user.profile, amount= amount, wallet='main', status='approved', approved=True)
                            new_withdrawal.save()

                            new_tnx = Transaction(amount=amount, txn_code=new_withdrawal.txn_code, user = self.request.user.profile, txn_method="manual", txn_type='withdrawal', approved=True)
                            new_tnx.save()
                            
                            wallet = InvestmentWallet.objects.get(user=self.request.user.profile)
                            wallet.balance -= amount
                            wallet.save()

                            flex_wallet.deposit += amount
                            flex_wallet.save()
                            new_notification = UserNotifications(user=self.request.user.profile, message=f"You have withrawn {new_withdrawal.amount} to your Flex wallet ")
                            new_notification.save()
                            return HttpResponseRedirect(reverse('wallet:wallets'))
                        else:
                            print("Your balance is less than the requested amount")
                            messages.error(self.request, f"Your balance is less than the requested amount, Please choose a lesser amount")
                            return HttpResponseRedirect(reverse('wallet:withdraw', kwargs={'wallet':self.kwargs['wallet']}))

                    
                elif self.kwargs['wallet'] == 'referral':
                    wallet = ReferralWallet.objects.get(user = self.request.user.profile)
                    if int(amount) <= wallet.balance:
                        new_withdrawal = Withdrawal(txn_code = transaction_code, user= self.request.user.profile, amount= amount, wallet='referrals')
                        new_withdrawal.save()

                        new_tnx = Transaction(amount=amount, txn_code=new_withdrawal.txn_code, user = self.request.user.profile, txn_method="manual", txn_type='referral_earnings')
                        new_tnx.save()

                        
                        wallet.balance -= amount
                        wallet.save()
                        
                        referral_profit_withrawal_request.delay(self.request.user.pk, new_withdrawal.txn_code)

                        

                        new_notification = UserNotifications(user=self.request.user.profile, message=f"Your withrawal request of  {new_withdrawal.amount} has been received ")
                        new_notification.save()
                        #SEND EMAIL TO ADMIN HERE
                        return redirect(reverse('wallet:withdrawal-request-sent',  kwargs={'transaction_code' : new_withdrawal.txn_code}))
                    else:
                        print("Your balance is less than the requested amount")
                        messages.error(self.request, f"Your balance is less than the requested amount, Please choose a lesser amount")
                        return HttpResponseRedirect(reverse('wallet:withdraw', kwargs={'wallet':self.kwargs['wallet']}))

                elif self.kwargs['wallet'] == 'flex_wallet':
                    wallet = MainWallet.objects.get(user = self.request.user.profile)
                    if int(amount) <= wallet.deposit:
                        new_withdrawal = Withdrawal(txn_code = transaction_code, user= self.request.user.profile, amount= amount, wallet='main')
                        new_withdrawal.save()

                        new_tnx = Transaction(amount=amount, txn_code=new_withdrawal.txn_code, user = self.request.user.profile, txn_method="manual", txn_type='withdrawal')
                        new_tnx.save()

                        wallet.deposit -= int(amount)
                        wallet.save()
                        
                        flex_wallet_withrawal_request.delay(self.request.user.pk, new_withdrawal.txn_code)

                        new_notification = UserNotifications(user=self.request.user.profile, message=f"Your withrawal request of  {new_withdrawal.amount} has been received ")
                        new_notification.save()

                        return redirect(reverse('wallet:withdrawal-request-sent',  kwargs={'transaction_code' : new_withdrawal.txn_code}))


                    else:
                        print("Your flex wallet balance is less than the requested amount")
                        messages.error(self.request, f"Your flex wallet balance is less than the requested amount, Please choose a lesser amount")
                        return HttpResponseRedirect(reverse('wallet:withdraw', kwargs={'wallet':self.kwargs['wallet']}))
                print(amount)
            else:
                print("Form is not valid")
                print(form.errors)
            return HttpResponseRedirect(reverse('wallet:withdraw', kwargs={'wallet':self.kwargs['wallet']}))
        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise
                

 
@login_required
def withdraw_request_sent(request, transaction_code):

    withdrawal= Withdrawal.objects.filter(txn_code=transaction_code).first()

    user_bank = UserBankAccount.objects.filter(user=request.user.profile).first()

    if user_bank:
        print("Yes")
        print(user_bank.account_name)


    template = 'wallet/withdrawal_request_sent.html'

    context = {
        'withdrawal':withdrawal,
        'user_bank':user_bank
    }

    return render(request, template, context)

@login_required
def check_balance(request):

    data = {}
    amount = request.GET.get('amount', None)
    user = request.GET.get('user', None)
    which_wallet = request.GET.get('which_wallet', None)
    print(user)
    print(amount)
    profile = Profile.objects.filter(user=request.user).first()
    print(profile)
    balance = 0
    if which_wallet == 'investment':
        wallet = InvestmentWallet.objects.filter(user=profile).first()
        balance = wallet.balance
    elif which_wallet == 'referral':
        wallet = ReferralWallet.objects.filter(user=profile).first()
        balance = wallet.balance
    elif which_wallet == 'flex_wallet':
        wallet = MainWallet.objects.filter(user=profile).first()
        balance = wallet.deposit
    print(balance)

    data.update({'my_balance':balance})
    
    return JsonResponse(data)




@login_required
def cancel_user_deposit(request, transaction_code):
    deposit = Deposit.objects.filter(txn_code=transaction_code).first()
    if deposit:
        deposit.delete()
        return redirect('wallet:dashboard')   
    else:
        messages.info(request, "The transaction does not exist")
        print("The transaction does not exist")
        return redirect('wallet:dashboard')

@login_required
def cancel_user_withdrawal(request, transaction_code):
    withdrawal = Withdrawal.objects.filter(txn_code=transaction_code).first()
    flex_wallet = MainWallet.objects.filter(user=request.user.profile).first()
    if withdrawal:
        flex_wallet.deposit += int(withdrawal.amount)
        flex_wallet.save() 
        withdrawal.delete()
        return redirect('wallet:dashboard')   
    else:
        messages.info(request, "The transaction does not exist")
        print("The transaction does not exist")
        return redirect('wallet:dashboard')


@require_POST
@csrf_exempt
def monnify_test_webhook_view(request):
    print("This is an api webhook from monnify")
    new_wbh = WebhookBackup.objects.create(pay_sol="monnify")
    payload = json.loads(request.body)
    print(payload)

    new_wbh.req_body = json.dumps(payload)
    new_wbh.save()

   

    paymentReference = payload['paymentReference']
    amountPaid = payload['amountPaid']
    paidOn = payload['paidOn']
    transactionReference = payload['transactionReference']
    transactionHash = payload['transactionHash']

    
    

    hashbale_string = f"{monnify_secret_key}|{paymentReference}|{amountPaid}|{paidOn}|{transactionReference}"
    trans_hash = hashlib.sha512( hashbale_string.encode("utf-8") ).hexdigest()
    print(trans_hash)

    if transactionHash == trans_hash:
        print("API correct")
        #call the verification api again 
        auth_string = f"{monnify_api_key}:{monnify_secret_key}"
        auth_string_bytes = auth_string.encode("ascii") 
        encoded = base64.b64encode(auth_string_bytes)
        print(encoded)
        encoded_raw = encoded.decode('ascii')
        print(encoded_raw)
        get_basic_headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Basic {encoded_raw}"
                }
        get_basic = requests.post(f"{monnify_base_url}/api/v1/auth/login", headers=get_basic_headers)

        get_basic_auth_response = get_basic.json()
        print(get_basic_auth_response)

        accessToken = get_basic_auth_response['responseBody']['accessToken']

        headers = {'Authorization': f'Bearer {accessToken}'}
        resp = requests.get(
            f"{monnify_base_url}/api/v2/transactions/{transactionReference}", headers=headers)
        response = resp.json()
        print(response)

        try:
            status = response['responseMessage']
            if status == "success":
                payment_status = response['responseBody']['paymentStatus']
                if payment_status == "PAID":
                    get_trans = Transaction.objects.filter(txn_code=paymentReference).first()
                    if int(get_trans.amount) == int(float(amountPaid)):
                        print("the correct trans actually!")
                        if get_trans.approved == True:
                            get_trans.trans_ref = transactionReference
                            get_trans.save()
                            return HttpResponse(status=200)
                        else:
                            check_deposit = Deposit.objects.filter(txn_code = get_trans.txn_code, user = get_trans.user, amount = int(get_trans.amount)).first()
                            if check_deposit and check_deposit.approved == True:
                                return HttpResponse(status=200)
                            else:
                                new_deposit = Deposit.objects.create(txn_code = get_trans.txn_code, user = get_trans.user, amount=int(get_trans.amount), status='approved', wallet="main", approved=True,trans_ref=transactionReference)
                                get_trans.trans_ref = transactionReference
                                get_trans.save()
                                the_wallet = MainWallet.objects.filter(user=new_deposit.user).first()
                                print(the_wallet)
                                the_wallet.deposit += int(new_deposit.amount)
                                the_wallet.save()
                                send_webhook_value_added.delay(the_wallet.user.user.pk, new_deposit.txn_code)
                                new_wbh.the_trans = get_trans
                                new_wbh.approved = True
                                new_wbh.save()
                                return HttpResponse(status=200)
            else:
                err_msg = "Transaction status was failed "
                send_wallet_generated_error.delay(err_msg)
                return HttpResponse(status=200)

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
            send_wallet_generated_error.delay(err_msg)
            return HttpResponse(status=200)
            

        except:
            print("Unexpected Error")
            err_msg = "Unexpected Error Happened"
            send_wallet_generated_error.delay(err_msg)
            return HttpResponse(status=200)
            
    else:
        err_msg = "Transaction Hash does not match"
        send_wallet_generated_error.delay(err_msg)
        return HttpResponse(status=200)
        



@require_POST
@csrf_exempt
def monnify_test_webhook_view_sandbox(request):
    print("This is an api webhook from monnify")
    new_wbh = WebhookBackup.objects.create(pay_sol="monnify")
    payload = json.loads(request.body)
    print(payload)


    paymentReference = payload['paymentReference']
    amountPaid = payload['amountPaid']
    paidOn = payload['paidOn']
    transactionReference = payload['transactionReference']
    transactionHash = payload['transactionHash']

    
    hashbale_string = f"{monnify_secret_key}|{paymentReference}|{amountPaid}|{paidOn}|{transactionReference}"
    trans_hash = hashlib.sha512( hashbale_string.encode("utf-8") ).hexdigest()
    print(trans_hash)

    if transactionHash == trans_hash:
        print("API correct")
        #call the verification api again 
        auth_string = f"{monnify_api_key}:{monnify_secret_key}"
        auth_string_bytes = auth_string.encode("ascii") 
        encoded = base64.b64encode(auth_string_bytes)
        print(encoded)
        encoded_raw = encoded.decode('ascii')
        print(encoded_raw)
        get_basic_headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Basic {encoded_raw}"
                }
        get_basic = requests.post(f"{test_monnify_base_url}/api/v1/auth/login", headers=get_basic_headers)

        get_basic_auth_response = get_basic.json()
        print(get_basic_auth_response)

        accessToken = get_basic_auth_response['responseBody']['accessToken']

        headers = {'Authorization': f'Bearer {accessToken}'}
        resp = requests.get(
            f"{test_monnify_base_url}/api/v2/transactions/{transactionReference}", headers=headers)
        response = resp.json()
        print(response)

        try:
            status = response['responseMessage']
            if status == "success":
                payment_status = response['responseBody']['paymentStatus']
                if payment_status == "PAID":
                    get_trans = Transaction.objects.get(trans_ref=transactionReference)
                    if int(get_trans.amount) == int(amountPaid):
                        print("the correct trans actually!")
                        if get_trans.approved == True:
                            return HttpResponse(status=200)
                        else:
                            get_deposit, created = Deposit.objects.get_or_create(txn_code = get_trans.txn_code, user = get_trans.user, amount=get_trans.amount, status='approved', wallet="main", approved=True,trans_ref=get_trans.trans_ref)
                            the_wallet = MainWallet.objects.get(user=get_deposit.user)
                            print(the_wallet)
                            the_wallet.deposit += int(get_deposit.amount)
                            the_wallet.save()
                            send_webhook_value_added.delay(the_wallet.user.user.pk, get_deposit.txn_code)
                            new_wbh.the_trans = get_trans
                            new_wbh.approved = True
                            new_wbh.save()
                            return HttpResponse(status=200)
            else:
                send_wallet_generated_error.delay()
                return HttpResponse(status=200)

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
            send_wallet_generated_error.delay()
            return HttpResponse(status=200)
            

        except:
            print("Unexpected Error")
            send_wallet_generated_error.delay()
            return HttpResponse(status=200)
            
    else:
        send_wallet_generated_error.delay()
        return HttpResponse(status=200)
        
