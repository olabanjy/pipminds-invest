from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, reverse, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.encoding import force_bytes
from paystackapi.paystack import Paystack
from django.db.models import Sum
from .forms import *
from .models import *
from wallet.models import *
from investment.models import *
from .utils import *
from .tasks import *
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.timezone import make_aware

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
import pandas as pd
import time
import random, string
from decimal import Decimal
from django.contrib.humanize.templatetags.humanize import intcomma
import math

from datetime import timedelta, date, datetime, time
from dateutil.relativedelta import relativedelta

paystack_secret_key = settings.PAYSTACK_SECRET_KEY

flutterwave_secret_key = settings.FLUTTERWAVE_SECRET_KEY

paystack = Paystack(secret_key=paystack_secret_key)

#PROFILE DASHBOARD VIEWS 

class ProfileDashboard(View):
    def get(self, request, *args, **kwargs):


        template = 'profile/dashboard.html'
        daytime = time_of_day()
        user_sub = get_user_subscription(self.request)
        print(user_sub)
        print(user_sub.active)
        context = {
            'user_sub': user_sub, 
            'daytime': daytime
        }

        return render(self.request, template, context)

class MySubscription(View):
    def get(self, request, *args, **kwargs):


        template = 'profile/my_subscriptions.html'
        user_sub = get_user_subscription(self.request)
        print(user_sub)
        context = {
            'user_sub': user_sub
        }

        return render(self.request, template, context)

class PPPDetails(View):
    def get(self, request, *args, **kwargs):

        template = 'profile/my_subscription_detail.html'
        user_sub = get_user_subscription(self.request)
        print(user_sub)
        premium_sub = Membership.objects.get(membership_type="premium")
        user_wallet = MainWallet.objects.filter(user=self.request.user.profile).first()
        flex_balance = user_wallet.deposit
        context = {
            'user_sub': user_sub, 
            'premium_sub': premium_sub,
            'flex_balance':flex_balance
        }

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):
        user_membership = get_user_membership(request)
        if user_membership.paystack_customer_id is None or user_membership.paystack_customer_id == '':
            user_membership.paystack_customer_id = self.request.user.profile.user_code
            user_membership.paystack_unique_user_id = self.request.user.profile.user_code
            user_membership.save()
        premium_sub = Membership.objects.get(membership_type="premium")
        selected_membership_type = premium_sub.membership_type
        print(selected_membership_type)
        selected_membership_qs = Membership.objects.filter(
            membership_type=selected_membership_type)
        if selected_membership_qs.exists():
            selected_membership = selected_membership_qs.first()
        request.session['selected_membership_type'] = selected_membership.membership_type
        tranx_id = request.POST['flutterTranxID']
        tranx_ref = request.POST['flutterTranxRef']
        print(tranx_id)
        print(tranx_ref)
        transaction_code = str(''.join(random.choices(string.digits, k = 13)))
        headers = {'Authorization': f'Bearer {flutterwave_secret_key}'}
        resp = requests.get(
            f"https://api.flutterwave.com/v3/transactions/{tranx_id}/verify", headers=headers)
        response = resp.json()
        print(response['data']['tx_ref'])
        print(response['status'])
        try:
            print(response)
            
            status = response['status']
            response_tranx_ref = response['data']['tx_ref']
            if status == "success" and tranx_ref == response_tranx_ref:
                print("YES")

                new_sub_instance_id = str(''.join(random.choices(string.digits, k = 9)))

                new_sub_instance, created = SubscriptionInstance.objects.get_or_create(txn_code=new_sub_instance_id, user=self.request.user.profile)
                

                print("The card was charged")
                messages.success(request, "Your card was charged !")
                return redirect(reverse('users:update-subscription',
                                        kwargs={
                                            'subscription_id': new_sub_instance.txn_code
                                        }
                                        ))
            else:
                messages.warning(self.request, 'Payment failed')
                return HttpResponseRedirect(reverse('users:subscription-detail'))
                
        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise

@login_required
def updateSubscription(request, subscription_id):
    user_membership = get_user_membership(request)
    selected_membership = get_selected_membership(request)
    print(f" the user membership before is {user_membership}")
    print(f"the selected membership type is {selected_membership}")

    user_membership.membership = selected_membership
    user_membership.save()

    print(f"the user membership now is  {user_membership.membership}")


    sub, created = Subscription.objects.get_or_create(
        user_membership=user_membership)
    sub.paystack_subscription_id = subscription_id
    sub.active = True
    sub.save()

    sub_instance = SubscriptionInstance.objects.get(txn_code=subscription_id)
    print(f"sub instance is {sub_instance}")
    sub_instance.subscription = sub 
    sub_instance.save()

    profile = request.user.profile
    print(f"user ppp started status before is {profile.ppp_started}")
    print(f"user ppp verified status before is {profile.ppp_verfied}")
    profile.ppp_started = True
    profile.ppp_verfied = True
    profile.save()

    print(f"user ppp started status after is {profile.ppp_started}")
    print(f"user ppp verified status after is {profile.ppp_verfied}")

    

    try:
        del request.session['selected_membership_type']
    except:
        pass
    messages.info(request, f'successfully created {selected_membership} membership')


    contract_data = {
                    'first_name':request.user.profile.first_name,
                    'last_name':request.user.profile.last_name,
                    'today':datetime.astimezone(datetime.today()) ,
                    'address_1':request.user.profile.address_1,
                    'address_2':request.user.profile.address_2,
                    'city':request.user.profile.city,
                    'state':request.user.profile.state,
                                              
             }

    contract_filename = f"PPP_AGREEMENT_{sub_instance.txn_code}.pdf"

    new_render_to_file_ppp_sub('contracts/ppp_contract.html',contract_filename, sub_instance.txn_code, contract_data)

    send_congratulations_email.delay(request.user.pk,sub_instance.pk, contract_filename)
    #send_receipt(request.user.pk, user_membership.pk)

    

    new_notification = UserNotifications(user=request.user.profile, message="Your PPP subscribtion has been activated")
    new_notification.save()

    return redirect('users:ppp-dashboard')


@login_required
def cancelSubscription(request):
    user_sub = get_user_subscription(request)

    if user_sub.active == False:
        messages.info(request, "You do not have an active subscription ! ")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    

    user_sub.active = False
    user_sub.save()

    free_membership = Membership.objects.filter(
        membership_type='free').first()
    user_membership = get_user_membership(request)
    user_membership.membership = free_membership
    user_membership.save()

    messages.info(
        request, "Successfully cancelled membership. We have sent an email")

    return redirect('users:subscription')





#MANAGE REFERRAL TREE

class ManageReferrals(View):
    def get(self, request, *args, **kwargs):
        template = 'profile/manage_referral.html'
    
        
        profile = Profile.objects.get(user=self.request.user)

        if not profile.profile_set_up:
            return redirect('users:profile-set-up')
        

        context = {
        }

        return render(self.request, template, context)

@login_required
def ppp_dashboard(request):
 
    if request.user.profile.ppp_started == False:
        return redirect('users:ppp-onboarding')
    
    if request.user.profile.ppp_verfied == False:
        return redirect('users:subscription-detail')
        
   

    
    
    template = 'profile/dashboard.html'
    daytime = time_of_day()
    context={
        'daytime':daytime
    }
    return render(request, template, context)



@login_required
def ppp_onboarding(request):
    template = 'users/ppp_onboarding.html'

    date_today  =  datetime.now()
    context = {
        'today':date_today

    }
    return render(request, template, context)

@login_required
def ppp_get_started(request):
    user_membership = get_user_membership(request)
    if user_membership.paystack_customer_id is None or user_membership.paystack_customer_id == '':
        user_membership.paystack_customer_id = request.user.profile.user_code
        user_membership.paystack_unique_user_id = request.user.profile.user_code
        user_membership.save()
    profile = request.user.profile
    if profile:
        profile.ppp_started = True
        profile.save()
        print(f"user status after clicking getting started is {profile.ppp_started}")
        return redirect('users:subscription-detail')
    else:
        print("Some Errors occured!")
        return redirect('users:ppp-onboarding')
    
     


#ACCOUNT SETTINGS 
class AccountSettings(View):
    def get(self, request, *args, **kwargs):

        template = 'profile/my_profile.html'
        p_form = UpdateProfileForm()
        a_form = UpdateAddressForm()
        
        bank_details = UserBankAccount.objects.filter(user=self.request.user.profile).first()
        next_of_kin = NextOfKin.objects.filter(user=self.request.user.profile).first()

        context = {
            'bank_details':bank_details,
            'p_form': p_form,
            'a_form': a_form,
            'next_of_kin': next_of_kin

        }

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):
        p_form = UpdateProfileForm(self.request.POST or None)
        a_form = UpdateAddressForm(self.request.POST or None)

        try:
            profile = Profile.objects.get(user=self.request.user)
            if p_form.is_valid():
                first_name = p_form.cleaned_data.get('first_name')
                last_name = p_form.cleaned_data.get('last_name')
                phone = p_form.cleaned_data.get('phone')
                dob = p_form.cleaned_data.get('dob')

                profile.first_name = first_name
                profile.last_name = last_name
                profile.phone = phone 
                profile.dob = dob
                profile.save()


            elif a_form.is_valid():
                address_1 = a_form.cleaned_data.get('address_1')
                address_2 = a_form.cleaned_data.get('address_2')
                state = a_form.cleaned_data.get('state')
                nationality = a_form.cleaned_data.get('nationality')

                profile.address_1 = address_1
                profile.address_2 = address_2
                profile.state = state
                profile.nationality = nationality
                profile.save()

                return HttpResponseRedirect(reverse("users:profile-settings"))

            return HttpResponseRedirect(reverse("users:profile-settings"))



        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise



class ProfilePreference(View):
    def get(self, request, *args, **kwargs):

        template = 'profile/profile_preference.html'
        context = {}
        return render(self.request, template, context)

@login_required
def activate_wallet_remit(request):
    data = {}
    user_profile = request.user.profile
    user_profile.remit_inv_funds_to_wallet = True
    user_profile.save()
    data.update({'status':True}) 
    return JsonResponse(data)

@login_required
def deactivate_wallet_remit(request):
    data = {}
    user_profile = request.user.profile
    user_profile.remit_inv_funds_to_wallet = False
    user_profile.save()
    data.update({'status':True}) 
    return JsonResponse(data)
    





#ACCOUNT SET UP AND KYC 
class CompleteProfile(View):
    template = 'users/profile_set_up.html'
    def get(self, request, *args, **kwargs):

        if self.request.user.profile.profile_set_up == True:
            return redirect('/')

        elif self.request.user.profile.cip_pioneer_member == True:
            return redirect('/')

        elif self.request.user.profile.pioneer_ppp_member == True:
            return redirect('/')

        form = ProfileSetUpForm()
        context = {
            'form':form
        }

        return render(self.request, self.template, context)
    def post(self, request,  *args, **kwargs):
        form = ProfileSetUpForm(self.request.POST or None)
        try:
            profile = Profile.objects.get(user=self.request.user)
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                phone = form.cleaned_data.get('phone')
                dob = form.cleaned_data.get('dob')
                address_1 = form.cleaned_data.get('address_1')
                address_2 = form.cleaned_data.get('address_2')
                city = form.cleaned_data.get('city')
                state = form.cleaned_data.get('state')
                zip_code = form.cleaned_data.get('zip_code')
                nationality = form.cleaned_data.get('nationality')
                ref_code = form.cleaned_data.get('ref_code')
                print(ref_code)
                print(nationality)
                

                profile.first_name = first_name
                profile.last_name = last_name
                profile.phone = phone 
                profile.dob = dob
                profile.address_1 = address_1
                profile.address_2 = address_2
                profile.city = city
                profile.state = state
                profile.zip_code = zip_code
                profile.nationality = nationality
                profile.profile_set_up = True
                profile.save()

                if ref_code:
                    new_ref, created = Referral.objects.get_or_create(sponsor_id = ref_code, downline_id= profile.user_code)
                    sponsor = Profile.objects.filter(user_code=ref_code).first()
                    new_user_referral, created = UserReferrals.objects.get_or_create(sponsor=sponsor,downline=profile)
                    send_referal_email_to_sponsor.delay(sponsor.user.pk)

                    new_notification = UserNotifications(user=sponsor, message=f"Hurray! {profile.first_name} {profile.last_name} just signed up using your referal code.")
                    new_notification.save()
                

                user_bank_account, created = UserBankAccount.objects.get_or_create(user=profile)
                next_of_kin, created = NextOfKin.objects.get_or_create(user=profile)
                user_document, created = UserDocument.objects.get_or_create(user=profile)
                user_wallet, created = MainWallet.objects.get_or_create(user=profile)
                user_investment_wallet, created = InvestmentWallet.objects.get_or_create(user=profile)
                user_referral_wallet, created = ReferralWallet.objects.get_or_create(user=profile)
                send_profile_verified_email.delay(self.request.user.pk)
 
                return HttpResponseRedirect(reverse("home:home"))

            return render(self.request, self.template, {'form':form})

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
            return render(self.request, self.template, {'form':form})
        except:
            print("Unexpected Error")
            raise
            

@login_required
def check_sponsor(request):
    data = {}
    ref_code = request.GET.get('ref_code', None)
    sponsor = Profile.objects.filter(user_code=ref_code).first()
    print(ref_code)
    if sponsor and ref_code != request.user.profile.user_code:
        print("Sponsor Exists")
        print(sponsor)
        print(sponsor.first_name)
        data.update({'status':True,'first_name':sponsor.first_name.upper(), 'last_name': sponsor.last_name.upper()})
    else:
        print("No sponsor found")
        data.update({'status':False,'first_name':'', 'last_name': '' })
    
    return JsonResponse(data)

 
class InvestmentKYC(View):
    template = 'users/investment_kyc.html'
    def get(self, request,  *args, **kwargs):
        profile = self.request.user.profile
        if profile.investement_verified == 'approved':
            return redirect('/')
       
        form = InvestmentKYCForm()
        context = {
            'form':form
        }

        return render(self.request, self.template, context)

    def post(self, request,  *args, **kwargs):
        form = InvestmentKYCForm(self.request.POST, self.request.FILES or None)
        try:
            profile = Profile.objects.get(user=self.request.user)
            user_bank_account = UserBankAccount.objects.get(user=profile)
            user_document = UserDocument.objects.get(user=profile)
            user_next_of_kin = NextOfKin.objects.get(user=profile)
            if form.is_valid():
                
                bank_name = form.cleaned_data.get('bank_name')
                account_name = form.cleaned_data.get('account_name')
                account_number = form.cleaned_data.get('account_number')
                swift_code = form.cleaned_data.get('swift_code')

                doc_type = form.cleaned_data.get('doc_type')
                document_front = form.cleaned_data.get('document_front')
                document_back = form.cleaned_data.get('document_back')

                next_of_kin_fullname = form.cleaned_data.get('next_of_kin_fullname')
                next_of_kin_email = form.cleaned_data.get('next_of_kin_email')
                next_of_kin_phone = form.cleaned_data.get('next_of_kin_phone')

                user_bank_account.bank_name = bank_name
                user_bank_account.account_name = account_name
                user_bank_account.account_number = account_number
                user_bank_account.swift_code = swift_code
                user_bank_account.save()

                user_next_of_kin.full_name = next_of_kin_fullname
                user_next_of_kin.email = next_of_kin_email
                user_next_of_kin.phone = next_of_kin_phone
                user_next_of_kin.save()


                user_document.doc_front = document_front
                user_document.doc_back = document_back
                if doc_type == 0:
                    user_document.doc_type = 'passport'
                elif doc_type == 1:
                    user_document.doc_type = 'driving_license'
                else:
                    user_document.doc_type = 'national_id'
                user_document.save()

                profile.investment_kyc_submitted = True
                profile.investement_verified = "pending"
                profile.save()
                
                print(doc_type)

                send_kyc_submitted_email.delay(self.request.user.pk)
                send_kyc_submitted_email_admin.delay(self.request.user.pk)
                # Return to Pending KYC Approval 
                return HttpResponseRedirect(reverse("investment:dashboard"))
               
            else:
                print("Form is not valid")
                print(form.errors)

            return render(self.request, self.template, {'form':form})

        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise

@login_required
def restart_onboarding(request):

    profile = request.user.profile
    if profile.investment_kyc_submitted == True:
        profile.investment_kyc_submitted = False
    if profile.profile_set_up == True:
        profile.profile_set_up = False
    profile.save()

    return redirect('users:profile-set-up')


@login_required
def check_account_details(request):
    data = {}
    acct_num = request.GET.get('acct_num', None)
    print(acct_num)

    try:
        if len(acct_num) == 10:

            resp = requests.get(f"https://app.nuban.com.ng/api/{NUBAN_API_KEY}?acc_no={acct_num}")
            response =resp.json()

            for account in response:
                if request.user.profile.first_name.lower() in account['account_name'].lower() or request.user.profile.last_name.lower() in account['account_name'].lower():
                    position = response.index(account)
                    user_real_account = response[position]
                    account_name = user_real_account['account_name']
                    bank_name = user_real_account['bank_name']

                    data.update({'status':True,'msg': f'{bank_name} - {account_name}', 'acct_name':account_name, 'bank_name': bank_name })
                else:
                    data.update({'status':False,'msg': 'Your personal details does not match this account number. Please make sure to use your own account number'})
                    
        else:

            data.update({'status':False,'msg': 'Account Number must be 10 digits'})
        

    except KeyError:
        data.update({'status':False,'msg': 'We could not verify your account number'})

    except (ValueError, NameError, TypeError, ImportError, IndexError, AttributeError ) as error:
        err_msg = str(error)
        data.update({'status':False,'msg': 'We could not verify your account number'})
        print(err_msg)

    return JsonResponse(data)


























#MIGRATION VIEWS ------------------ STAY OFF 


# class ADMIN_USER_IMPORT(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         User = get_user_model()
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():
                   
#                     print(row['email address'])

#                     the_user_email = str(row['email address']).lower().strip() 
#                     the_user = User.objects.get(email=the_user_email)
#                     the_user_profile = the_user.profile

#                     if the_user_profile:
#                         print(the_user_profile.first_name)
#                         check_sponsor_email = str(row['referred by']).lower().strip()
#                         print(f"sponsor email is {check_sponsor_email}")
#                         if check_sponsor_email:
#                             check_sponsor = User.objects.get(email=str(check_sponsor_email))
#                             sponsor_profile = check_sponsor.profile
#                             if sponsor_profile:
#                                 print(sponsor_profile.first_name)

#                                 if sponsor_profile != the_user_profile:
#                                     new_ref, created = Referral.objects.get_or_create(sponsor_id=sponsor_profile.user_code, downline_id=the_user_profile.user_code)

#                                     new_user_referral, created = UserReferrals.objects.get_or_create(sponsor=sponsor_profile,downline=the_user_profile)
                                    
#                                     print(f"new referral {sponsor_profile.first_name} is sponsor for {the_user_profile.first_name}")
#                                 else:
#                                     print("user cannot refer himself/herself")

#                             else:
#                                 print("sponsor profile does not exist")
                               
#                         else:
#                             print("sponsor email not in sheet, moving on to the next ")

                

#                 print("All users have been assigned")
#                 return HttpResponseRedirect(reverse("users:admin-import"))



            
#             return HttpResponseRedirect(reverse("users:admin-import"))
                

#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:admin-import"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:admin-import"))



# class ADMIN_USER_IMPORT(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         User = get_user_model()
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():
                   
#                     print(row['email address']) 

                                
#                     the_email =  str(row['email address']).lower().strip()
#                     print(the_email)
#                     the_user_password= f"{the_email.split('@', 1)[0]}{1234}"
#                     print(the_user_password)

                    
#                     user, created = User.objects.get_or_create(
#                         username=str(the_email.split("@", 1)[0]),
                    
#                     defaults={
#                         'email':the_email,
#                         'password': make_password(the_user_password)
#                     }
#                     )
                   
#                     print("i got stuck here 1")
                    
                    

#                     user_profile = user.profile
#                     print("i got stuck here 2")

#                     user_profile.user_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 8)))
#                     user_profile.phone = str(row['phone'])
#                     user_profile.first_name = str(row['first name'])
#                     user_profile.last_name = f"{str(row['surname'])} {str(row['other name'])}"
#                     the_pioneer_ppp_reg_expires = str(row['reg date'])
#                     month, day, year = the_pioneer_ppp_reg_expires.split('/')
#                     user_profile.pioneer_ppp_reg_expires = '-'.join((year, month, day))
#                     user_profile.pioneer_ppp_member = True
#                     user_profile.address_1 = str(row['residential address'])
#                     user_profile.state = str(row['state'])
#                     user_profile.nationality = str(row['nationality'])
#                     user_profile.profile_set_up = True
#                     user_profile.investment_kyc_submitted = True
#                     user_profile.investement_verified = "approved"
#                     user_profile.ppp_started = True
#                     user_profile.ppp_verfied = True 
#                     user_profile.save()
#                     print("i got stuck here 3")
                    

#                     user_bank_account, created = UserBankAccount.objects.get_or_create(user=user.profile)
#                     next_of_kin, created = NextOfKin.objects.get_or_create(user=user.profile)
#                     user_document, created = UserDocument.objects.get_or_create(user=user.profile)
#                     user_wallet, created = MainWallet.objects.get_or_create(user=user.profile)
#                     user_investment_wallet, created = InvestmentWallet.objects.get_or_create(user=user.profile)
#                     user_referral_wallet, created = ReferralWallet.objects.get_or_create(user=user.profile)

#                     print("i got stuck here 4")

#                     user_bank_account.bank_name = str(row['bank name'])
#                     user_bank_account.account_name = str(row['account name'])
#                     user_bank_account.account_number = str(row['account number'])
#                     user_bank_account.save()

#                     print(f"done with {str(row['email address'])}")

#                 print("All users have been imported")
#                 return HttpResponseRedirect(reverse("users:admin-import"))



            
#             return HttpResponseRedirect(reverse("users:admin-import"))
                

#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:admin-import"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:admin-import"))



# class SendPPPEmail(View):

#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)

#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)

#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():
#                     # time.sleep(15)
                   
#                     print(row['email address'])
#                     the_email =  str(row['email address']).lower().strip()
#                     print(the_email)
#                     the_user_password= f"{the_email.split('@', 1)[0]}{1234}"
#                     print(the_user_password)
#                     # the_user_password= f"{str(row['surname']).lower()}{1234}"

                    
#                     the_user = User.objects.get(email=the_email)
#                     partner = the_user.profile
#                     print(partner.first_name)

#                     if partner and partner.pioneer_ppp_member == True:

#                         subject, from_email, to = 'Welcome to Pipminds Invest', 'PIPMINDS INVEST<hello@pipminds.com>', [
#                         partner.user.email]
                        
#                         html_content = render_to_string(
#                             'events/old_ppp_welcome.html', {'email': partner.user.email, 'first_name': partner.first_name, 'last_name': partner.last_name, 'password':the_user_password, 'ref_code':partner.user_code })
#                         msg = EmailMessage(subject, html_content, from_email, to)
#                         msg.content_subtype = "html"
#                         msg.send()

                        
#                     else:
#                         print("Error occured 1")
                    
                    
#                 print("All emails have been sent ")
#                 return HttpResponseRedirect(reverse("users:send-ppp-email"))    


#             return HttpResponseRedirect(reverse("users:send-ppp-email"))

                    
        
#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:send-ppp-email"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:send-ppp-email"))











#CIP IMPORT 

# class CIP_USER_IMPORT(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         User = get_user_model()
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():

#                     plan_cat = InvestmentPlan.objects.get(percentage_interest=int(row['percentage(per/month)']))
#                     print(plan_cat)
                

#                     inv_started = str(row['investment started'])
#                     day, month, year = inv_started.split('/')
#                     investment_started = '/'.join((month, day, year))
#                     investment_started_date = datetime.strptime(investment_started, '%m/%d/%Y')
#                     print(investment_started_date)
                    
                   
                    

#                     inv_duration = int(row['investment duration'])
#                     investment_ends_date = investment_started_date + relativedelta(months=inv_duration)
#                     print(investment_ends_date)
                    
#                     the_email =  str(row['email']).lower().strip()
#                     print(the_email)  

#                     # get_user = User.objects.filter(email=the_email)
#                     get_user = User.objects.filter(email=the_email)

#                     if get_user.exists():
#                         the_user = get_user[0]
#                         print(the_user)
#                         print("Hurray, User exists")  

#                         if investment_ends_date < datetime.today():
#                             print("this investment has ended!")

#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                             new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = the_user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), mig_batch='five', cip_pioneer=True, active=False, completed=True)


#                             time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                             print(time_dif.days)

#                             new_user_investment.maturity_days = time_dif.days
#                             new_user_investment.save()

#                             currentMonth = datetime.now().month
#                             print(currentMonth)
#                             print(new_user_investment.created_at.month)
                            
#                         elif investment_ends_date > datetime.today():
                            
#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                             new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = the_user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), cip_pioneer=True, active=True, mig_batch='five', completed=False)


#                             time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                             print(time_dif.days)

#                             new_user_investment.maturity_days = time_dif.days
#                             new_user_investment.save()


#                             new_user_inv_earning = UserInvestmentEarnings.objects.create(user=the_user.profile,plan=new_user_investment, amount=0, active=True)
                            

#                             p = lambda x: x/100
#                             daily_percentage = (new_user_investment.plan.percentage_interest) / 30 
#                             ur_daily_earning = float(new_user_investment.amount) *p(daily_percentage)
#                             print(ur_daily_earning)

                             
                            
#                             today = datetime.astimezone(datetime.today())
                            
#                             start_date = new_user_investment.created_at
#                             end_date = new_user_investment.maturity_date

#                             the_range = pd.date_range(start=start_date, end=end_date,freq='30D').to_pydatetime().tolist()
#                             print(the_range)
#                             for i in the_range:
#                                 print(i.year)
#                                 if i.year == datetime.astimezone(datetime.now()).year:
                                
#                                     if  i.month ==  datetime.astimezone(datetime.now()).month and today > i:
#                                         ur_last_payout = i 
                                        
#                                         ur_next_payout = i + timedelta(30)

                                        
                                        
#                                         print(f"You have been paid for this month on the {ur_last_payout}, the next payout is {ur_next_payout}")
#                                         new_user_investment.next_payout = ur_next_payout
                                        
#                                         nos_days = (datetime.date(today) - datetime.date(ur_last_payout)).days
#                                         print(nos_days)

#                                         new_user_investment.profit_earned = int(ur_daily_earning * nos_days)
#                                         new_user_investment.save()

#                                         new_user_inv_earning.amount = int(ur_daily_earning * nos_days)
#                                         new_user_inv_earning.save()
                                        

                                        


#                                     elif i.month ==  datetime.astimezone(datetime.now()).month and today < i:
                                        
                                        
#                                         ur_next_payout = i
#                                         ur_last_payout = i -  timedelta(30)

#                                         print(f"Gbam, the next payout is {ur_next_payout}")
#                                         print(f"Last month was {ur_last_payout} ")

#                                         new_user_investment.next_payout = ur_next_payout
                                        

                                    
                                        
#                                         nos_days = (datetime.date(today) - datetime.date(ur_last_payout)).days
#                                         print(nos_days)

#                                         new_user_investment.profit_earned = int(ur_daily_earning * nos_days)
#                                         new_user_investment.save()

#                                         new_user_inv_earning.amount = int(ur_daily_earning * nos_days)
#                                         new_user_inv_earning.save()
#                                 else:
#                                     print(f"no be this year o, na {i.year}")
#                                 print(i)

#                     else:
                        
#                         the_user_password= f"{the_email.split('@', 1)[0]}{1234}"
#                         print(the_user_password)

#                         user, created = User.objects.get_or_create(
#                                 username=str(the_email.split("@", 1)[0]),

#                                 defaults={
#                                 'email':the_email,
#                                 'password': make_password(the_user_password)
#                             }

#                         )

#                         print(user.username)     

#                         print("i got stuck here 1")

#                         user_profile = user.profile
#                         print("i got stuck here 2")

#                         user_profile.user_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 8)))
#                         user_profile.phone = str(row['phone number'])
#                         user_profile.first_name = str(row['first name'])
#                         user_profile.last_name = str(row['last name'])
#                         user_profile.address_1 = str(row['residential address'])
#                         user_profile.state = str(row['state of origin'])
#                         user_profile.nationality = str(row['nationality'])
#                         user_profile.profile_set_up = True
#                         user_profile.investment_kyc_submitted = True
#                         user_profile.investement_verified = "approved"
#                         user_profile.cip_pioneer_member = True
#                         user_profile.save()
#                         print("i got stuck here 3")


#                         user_bank_account, created = UserBankAccount.objects.get_or_create(user=user.profile)
#                         next_of_kin, created = NextOfKin.objects.get_or_create(user=user.profile)
#                         user_document, created = UserDocument.objects.get_or_create(user=user.profile)
#                         user_wallet, created = MainWallet.objects.get_or_create(user=user.profile)
#                         user_investment_wallet, created = InvestmentWallet.objects.get_or_create(user=user.profile)
#                         user_referral_wallet, created = ReferralWallet.objects.get_or_create(user=user.profile)
#                         print("i got stuck here 4")


#                         user_bank_account.bank_name = str(row['bank name(in full)'])
#                         user_bank_account.account_name = str(row['account name'])
#                         user_bank_account.account_number = str(row['account number']).replace("'","")
#                         user_bank_account.save()

#                         print(f"done with {str(row['email'])}")

                        
#                         if investment_ends_date < datetime.today():
#                             print("this investment has ended!")

#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                             new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), cip_pioneer=True, mig_batch='five', completed=True, active=False)


#                             time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                             print(time_dif.days)

#                             new_user_investment.maturity_days = time_dif.days
#                             new_user_investment.save()

#                         elif investment_ends_date > datetime.today():

#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                             new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), cip_pioneer=True, mig_batch='five', active=True, completed=False)


#                             time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                             print(time_dif.days)

#                             new_user_investment.maturity_days = time_dif.days
#                             new_user_investment.save()


#                             new_user_inv_earning = UserInvestmentEarnings.objects.create(user=user.profile,plan=new_user_investment, amount=0, active=True)
                            

#                             p = lambda x: x/100
#                             daily_percentage = (new_user_investment.plan.percentage_interest) / 30 
#                             ur_daily_earning = float(new_user_investment.amount) *p(daily_percentage)
#                             print(ur_daily_earning)

                            
                            
#                             today = datetime.astimezone(datetime.today())
                            
#                             start_date = new_user_investment.created_at
#                             end_date = new_user_investment.maturity_date

#                             the_range = pd.date_range(start=start_date, end=end_date,freq='30D').to_pydatetime().tolist()
#                             print(the_range)
#                             for i in the_range:
#                                 print(i.year)
#                                 if i.year == datetime.astimezone(datetime.now()).year:
#                                     if i.month ==  datetime.astimezone(datetime.now()).month and today > i:
#                                         ur_last_payout = i 
                                        
#                                         ur_next_payout = i + timedelta(30)

                                        
                                        
#                                         print(f"You have been paid for this month on the {ur_last_payout}, the next payout is {ur_next_payout}")
#                                         new_user_investment.next_payout = ur_next_payout
                                        
#                                         nos_days = (datetime.date(today) - datetime.date(ur_last_payout)).days
#                                         print(nos_days)

#                                         new_user_investment.profit_earned = int(ur_daily_earning * nos_days)
#                                         new_user_investment.save()

#                                         new_user_inv_earning.amount = int(ur_daily_earning * nos_days)
#                                         new_user_inv_earning.save()
                                        

                                        


#                                     elif i.month ==  datetime.astimezone(datetime.now()).month and today < i:
                                        
                                        
#                                         ur_next_payout = i
#                                         ur_last_payout = i -  timedelta(30)

#                                         print(f"Gbam, the next payout is {ur_next_payout}")
#                                         print(f"Last month was {ur_last_payout} ")

#                                         new_user_investment.next_payout = ur_next_payout
                                        

                                    
                                        
#                                         nos_days = (datetime.date(today) - datetime.date(ur_last_payout)).days
#                                         print(nos_days)

#                                         new_user_investment.profit_earned = int(ur_daily_earning * nos_days)
#                                         new_user_investment.save()

#                                         new_user_inv_earning.amount = int(ur_daily_earning * nos_days)
#                                         new_user_inv_earning.save()
#                                 else:
#                                     print(f"no be this year or, na {i.year}")
 
#                                 print(i)

                        

#                 print("All users have been imported")
#                 return HttpResponseRedirect(reverse("users:cip-import"))



            
#             return HttpResponseRedirect(reverse("users:cip-import"))
                

#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:cip-import"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:cip-import"))



# class CIP_ASSIGN_SPONSOR(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         User = get_user_model()
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():
                   
#                     the_email =  str(row['email']).lower().strip()
#                     print(the_email)

#                     sponsor_email = str(row['email address']).lower().strip()
#                     print(sponsor_email)


                    
#                     the_user = User.objects.get(email=the_email)
#                     the_user_profile = the_user.profile

#                     if the_user_profile:
#                         print(the_user_profile.first_name)
                        
                        
#                         if sponsor_email:
#                             print(f"sponsor email is {sponsor_email}")
#                             check_sponsor = User.objects.filter(email=str(sponsor_email))
#                             if check_sponsor.exists():
#                                 sponsor_profile = check_sponsor[0].profile
#                                 if sponsor_profile:
#                                     print(sponsor_profile.first_name)

#                                     if sponsor_profile != the_user_profile:
#                                         new_ref, created = Referral.objects.get_or_create(sponsor_id=sponsor_profile.user_code, downline_id=the_user_profile.user_code)

#                                         new_user_referral, created = UserReferrals.objects.get_or_create(sponsor=sponsor_profile,downline=the_user_profile)
                                        
#                                         print(f"user {sponsor_profile.first_name} is now sponsor for {the_user_profile.first_name}")
#                                     else:
#                                         print("user cannot refer himself/herself")

#                                 else:
#                                     print("sponsor profile does not exist")
#                             else:
#                                 print("sponsor account does not exist")
                               
#                         else:
#                             print("sponsor email not in sheet, moving on to the next ")

                

#                 print("All users have been assigned")
#                 return HttpResponseRedirect(reverse("users:cip-user-assign"))



            
#             return HttpResponseRedirect(reverse("users:cip-user-assign"))
                

#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:cip-user-assign"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:cip-user-assign"))


# def check_multiple_sponsor(request):
#     data_col = ['UserProf', 'SponsorProf']
#     data = {
#             'UserProf':[],'SponsorProf':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     user_profiles = Profile.objects.all()
#     for prof in user_profiles:
#         user_sponsors = UserReferrals.objects.filter(downline=prof).all()
#         if user_sponsors.count() > 1:
#             print('more than one sponsor')
#             # print(user_sponsors.sponsor)
#             for the_profile in user_sponsors:
#                 print(the_profile)
#                 print(f"{the_profile.sponsor.user.email} -> {the_profile.downline.user.email}")
#                 data['UserProf'].append(the_profile.downline.user.email)
#                 data['SponsorProf'].append(the_profile.sponsor.user.email)
#                 # data.update({'the_user':the_profile.downline.user.email, 'the_sponsor': the_profile.sponsor.user.email })
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df.to_csv("the_file.csv", index = False, header=True)
#     context = {
#         'the_data':data
#     }
  
#     return render(request, template, context)



# def get_cip_investors(request):
#     data_col = ['Investor_Email', 'Investor_First_Name', 'Investor_Last_Name', 'Investor_Phone_Number', 'Investor_Address', 'Invested_Amount', 'Invested_Started', 'Investment_Type']
#     data = {
#             'Investor_Email':[],'Investor_First_Name':[], 'Investor_Last_Name':[], 'Investor_Phone_Number':[], 'Investor_Address':[], 'Invested_Amount':[],'Invested_Started':[], 'Investment_Type':[], 
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     #all_investments = UserInvestment.objects.filter(active=True,completed=False).all()
#     all_investments = UserInvestment.objects.filter(active=True, completed=False, hip_pioneer=False).all()
#     for inv in all_investments:
#         user_profile = inv.user

#         print(f"{user_profile.user.email} {user_profile.first_name}")
#         data['Investor_Email'].append(user_profile.user.email)
#         data['Investor_First_Name'].append(user_profile.first_name)
#         data['Investor_Last_Name'].append(user_profile.last_name)
#         data['Investor_Phone_Number'].append(user_profile.phone)
#         data['Investor_Address'].append(f"{user_profile.address_1} {user_profile.address_2}")
#         data['Invested_Amount'].append(f"{inv.amount}")
#         data['Invested_Started'].append(f"{inv.created_at.date()}")
#         data['Investment_Type'].append(f"{inv.plan.name} - {inv.plan.category.name}")
       
      
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     # new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv("cip_investors_raw.csv", index = False, header=True)
#     #new_df.to_csv("cip_investors_all_real.csv", index = False, header=True)
#     new_df.to_csv("hip_investors_all_real.csv", index = False, header=True)

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)


# def get_cip_users_only(request):
#     data_col = ['Investor_Email', 'Investor_First_Name', 'Investor_Last_Name', 'Investor_Default_Password']
#     data = {
#             'Investor_Email':[],'Investor_First_Name':[], 'Investor_Last_Name':[], 'Investor_Default_Password':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     cip_investments = UserInvestment.objects.filter(cip_pioneer=True,mig_batch="five").all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         if user_profile.ppp_verfied == False and user_profile.user.last_login == None:
#             print(f"{user_profile.user.email} {user_profile.first_name} {user_profile.user.last_login}")
#             data['Investor_Email'].append(user_profile.user.email)
#             data['Investor_First_Name'].append(user_profile.first_name)
#             data['Investor_Last_Name'].append(user_profile.last_name)
#             data['Investor_Default_Password'].append(f"{user_profile.user.email.split('@', 1)[0]}{1234}")
#         else:
#             print("User is either a parter or has login before")
#             print(user_profile.user.last_login)
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv("cip_investors_raw.csv", index = False, header=True)
#     new_df.to_csv("cip_investors_not_signed_in_only_two.csv", index = False, header=True)

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)



# def get_cip_users_only(request):
#     template = 'users/multiple_sponsor_check.html'
#     cip_investments = UserInvestment.objects.filter(cip_pioneer=True).all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         if user_profile.ppp_verfied == False and user_profile.user.last_login == None:
#             print(f"{user_profile.user.email} {user_profile.first_name} {user_profile.user.last_login} {user_profile.user.email.split('@', 1)[0]}{1234}")

#             subject, from_email, to = 'WELCOME TO PIPMINDS INVEST', 'PIPMINDS INVEST<hello@pipminds.com>', [
#             user_profile.user.email]
            
#             html_content = render_to_string(
#                 'events/new_nologin_cip.html', {'email': user_profile.user.email, 'first_name': user_profile.first_name, 'last_name': user_profile.last_name, 'password':f"{user_profile.user.email.split('@', 1)[0]}{1234}"})
#             msg = EmailMessage(subject, html_content, from_email, to)
#             msg.content_subtype = "html"
#             msg.send()
            
#         else:
#             print("User is either a parter or has login before")
#             print(user_profile.user.last_login)
   
#     context={}
  
#     return render(request, template, context)





# HIP IMPORT SCRIPTS 

# class HIP_USER_IMPORT(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         User = get_user_model()
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():

#                     plan_cat = InvestmentPlan.objects.get(percentage_interest=int(row['percentage(per/month)']))
#                     print(plan_cat)
                

#                     inv_started = str(row['investment started'])
#                     day, month, year = inv_started.split('/')
#                     investment_started = '/'.join((month, day, year))
#                     investment_started_date = datetime.strptime(investment_started, '%m/%d/%Y')
#                     print(investment_started_date)
                    
                   
                    

#                     inv_duration = int(row['investment duration'])
#                     investment_ends_date = investment_started_date + relativedelta(months=inv_duration)
#                     print(investment_ends_date)
                    
#                     the_email =  str(row['email']).lower().strip()
#                     print(the_email)  

#                     # get_user = User.objects.filter(email=the_email)
#                     get_user = User.objects.filter(email=the_email)

#                     if get_user.exists():
#                         the_user = get_user[0]
#                         print(the_user)
#                         print("Hurray, User exists")  

                            
#                         if investment_ends_date > datetime.today():
                            
#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                             new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = the_user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), hip_pioneer=True, active=True, mig_batch='one', completed=False)


#                             time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                             print(time_dif.days)

#                             new_user_investment.maturity_days = time_dif.days
#                             new_user_investment.next_payout = new_user_investment.maturity_date
#                             new_user_investment.save()


#                             new_user_inv_earning = UserInvestmentEarnings.objects.create(user=the_user.profile,plan=new_user_investment, amount=0, active=True)
                            

#                             p = lambda x: x/100
#                             daily_percentage = (new_user_investment.plan.percentage_interest) / int(new_user_investment.maturity_days)
#                             print(daily_percentage) 
#                             ur_daily_earning = float(new_user_investment.amount) *p(daily_percentage)
#                             print(ur_daily_earning)

                            
                             
#                             today = datetime.astimezone(datetime.today())
                            
#                             start_date = new_user_investment.created_at
#                             end_date = new_user_investment.maturity_date

#                             nos_days_earned = (datetime.date(today) - datetime.date(start_date)).days
#                             print(nos_days_earned)

#                             new_user_investment.profit_earned = int(ur_daily_earning * nos_days_earned)
#                             new_user_investment.save()


#                             new_user_inv_earning.amount = int(ur_daily_earning * nos_days_earned)
#                             new_user_inv_earning.save()
#                         else:
#                             print("Something went wrong, pls check !")

#                     else:
#                         the_user_password= f"{the_email.split('@', 1)[0]}{1234}"
#                         print(the_user_password)

#                         user, created = User.objects.get_or_create(
#                                 username=str(the_email.split("@", 1)[0]),

#                                 defaults={
#                                 'email':the_email,
#                                 'password': make_password(the_user_password)
#                             }

#                         )

#                         print(user.username)     

#                         print("i got stuck here 1")

#                         user_profile = user.profile
#                         print("i got stuck here 2")

#                         user_profile.user_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 8)))
#                         user_profile.phone = str(row['phone number'])
#                         user_profile.first_name = str(row['first name'])
#                         user_profile.last_name = str(row['last name'])
#                         user_profile.address_1 = str(row['residential address'])
#                         user_profile.state = str(row['state of origin'])
#                         user_profile.nationality = str(row['nationality'])
#                         user_profile.profile_set_up = True
#                         user_profile.investment_kyc_submitted = True
#                         user_profile.investement_verified = "approved"
#                         user_profile.cip_pioneer_member = True
#                         user_profile.save()
#                         print("i got stuck here 3")


#                         user_bank_account, created = UserBankAccount.objects.get_or_create(user=user.profile)
#                         next_of_kin, created = NextOfKin.objects.get_or_create(user=user.profile)
#                         user_document, created = UserDocument.objects.get_or_create(user=user.profile)
#                         user_wallet, created = MainWallet.objects.get_or_create(user=user.profile)
#                         user_investment_wallet, created = InvestmentWallet.objects.get_or_create(user=user.profile)
#                         user_referral_wallet, created = ReferralWallet.objects.get_or_create(user=user.profile)
#                         print("i got stuck here 4")


#                         user_bank_account.bank_name = str(row['bank name(in full)'])
#                         user_bank_account.account_name = str(row['account name'])
#                         user_bank_account.account_number = str(row['account number']).replace("'","")
#                         user_bank_account.save()

#                         print(f"done with {str(row['email'])}")

                        
#                         if investment_ends_date > datetime.today():
                            
#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                             new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), hip_pioneer=True, active=True, mig_batch='one', completed=False)


#                             time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                             print(time_dif.days)

#                             new_user_investment.maturity_days = time_dif.days
#                             new_user_investment.next_payout = new_user_investment.maturity_date
#                             new_user_investment.save()


#                             new_user_inv_earning = UserInvestmentEarnings.objects.create(user=user.profile,plan=new_user_investment, amount=0, active=True)
                            

#                             p = lambda x: x/100
#                             daily_percentage = (new_user_investment.plan.percentage_interest) / int(new_user_investment.maturity_days)
#                             print(daily_percentage) 
#                             ur_daily_earning = float(new_user_investment.amount) *p(daily_percentage)
#                             print(ur_daily_earning)

                            
                             
#                             today = datetime.astimezone(datetime.today())
                            
#                             start_date = new_user_investment.created_at
#                             end_date = new_user_investment.maturity_date

#                             nos_days_earned = (datetime.date(today) - datetime.date(start_date)).days
#                             print(nos_days_earned)

#                             new_user_investment.profit_earned = int(ur_daily_earning * nos_days_earned)
#                             new_user_investment.save()


#                             new_user_inv_earning.amount = int(ur_daily_earning * nos_days_earned)
#                             new_user_inv_earning.save()
#                         else:
#                             print("Something went wrong, pls check !")

#                 print("All users have been imported")
#                 return HttpResponseRedirect(reverse("users:hip-import"))



            
#             return HttpResponseRedirect(reverse("users:hip-import"))
                

#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:hip-import"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:hip-import"))





# class HIP_ASSIGN_SPONSOR(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         User = get_user_model()
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():
                   
#                     the_email =  str(row['email']).lower().strip()
#                     print(the_email)

#                     sponsor_email = str(row['email address']).lower().strip()
#                     print(sponsor_email)


                    
#                     the_user = User.objects.get(email=the_email)
#                     the_user_profile = the_user.profile

#                     if the_user_profile:
#                         print(the_user_profile.first_name)
                        
                        
#                         if sponsor_email:
#                             print(f"sponsor email is {sponsor_email}")
#                             check_sponsor = User.objects.filter(email=str(sponsor_email))
#                             if check_sponsor.exists():
#                                 sponsor_profile = check_sponsor[0].profile
#                                 if sponsor_profile:
#                                     print(sponsor_profile.first_name)

#                                     if sponsor_profile != the_user_profile:
#                                         new_ref, created = Referral.objects.get_or_create(sponsor_id=sponsor_profile.user_code, downline_id=the_user_profile.user_code)

#                                         new_user_referral, created = UserReferrals.objects.get_or_create(sponsor=sponsor_profile,downline=the_user_profile)
                                        
#                                         print(f"user {sponsor_profile.first_name} is now sponsor for {the_user_profile.first_name}")
#                                     else:
#                                         print("user cannot refer himself/herself")

#                                 else:
#                                     print("sponsor profile does not exist")
#                             else:
#                                 print("sponsor account does not exist")
                               
#                         else:
#                             print("sponsor email not in sheet, moving on to the next ")

                

#                 print("All users have been assigned")
#                 return HttpResponseRedirect(reverse("users:hip-user-assign"))



            
#             return HttpResponseRedirect(reverse("users:hip-user-assign"))
                

#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:hip-user-assign"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:hip-user-assign"))








# class SendCIPEmail(View):

#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)

#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)

#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():
                    
#                     # time.sleep(15)
                   
#                     print(row['investor_email'])
#                     the_email =  str(row['investor_email']).lower().strip()
#                     print(the_email)
#                     the_user_password= f"{the_email.split('@', 1)[0]}{1234}"
#                     print(the_user_password)


                    
#                     the_user = User.objects.get(email=the_email)
#                     user_profile = the_user.profile
#                     print(user_profile.first_name)

                   

#                     subject, from_email, to = 'Welcome to Pipminds Invest', 'PIPMINDS INVEST<hello@pipminds.com>', [
#                     user_profile.user.email]

#                     html_content = render_to_string(
#                         'events/new_nologin_cip.html', {'email': user_profile.user.email, 'first_name': user_profile.first_name, 'last_name': user_profile.last_name, 'password':the_user_password})

#                     msg = EmailMessage(subject, html_content, from_email, to)
#                     msg.content_subtype = "html"
#                     msg.send()

                        
                 
                    
                    
#                 print("All emails have been sent ")
                 


#             return HttpResponseRedirect(reverse("users:send-cip-email"))

                    
        
#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:send-cip-email"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:send-cip-email"))


# def clear_ppp_earnings(request):

#     get_all_wallets = ReferralWallet.objects.all()
#     for wallet in get_all_wallets:
#         print(f" wallet balance was {wallet.balance}")
#         wallet.balance = 0
#         wallet.save()
#         print(f"wallet balance now {wallet.balance}")
#     print("All referal wallet cleared ! ")

#     return redirect('users:send-cip-email')

    


# def get_cip_payout(request):
#     data_col = ['Name', 'Invested_Amount',  'ROI', 'Account_Number', 'Bank', 'Payment_Preference']
#     data = {
#             'Name':[], 'Invested_Amount':[], 'ROI':[], 'Account_Number':[], 'Bank':[], 'Payment_Preference':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     today = datetime.date(datetime.astimezone(datetime.today()))
#     set_date_str = '27/03/21 00:00:00'
#     set_date = datetime.strptime(set_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(f"Set date is {set_date}")
#     cip_investments = UserInvestment.objects.filter(active=True,cip_pioneer=False,hip_pioneer=False).all()
#     #cip_investments = UserInvestment.objects.filter(active=True,cip_pioneer=True,completed=False).all()
#     for inv in cip_investments:
        
        
#         if inv.next_payout:
            
#             user_profile = inv.user     
#             if  inv.next_payout.date() == set_date:
#                 user_account = UserBankAccount.objects.filter(user=user_profile).first()
#                 user_earning = UserInvestmentEarnings.objects.filter(user=user_profile,plan=inv).first()
#                 print(f"Data is here for user {inv.user.user.email}")
#                 print(f"Investment amount is {inv.amount}")


#                 print(f"Investment Earning now is {user_earning.amount}")

#                 print(f"Investment Profit Earned is {inv.profit_earned}")



                
#                 p = lambda x: x/100
#                 daily_percentage = (inv.plan.percentage_interest) / 30 
#                 print(daily_percentage) 
#                 ur_daily_earning = float(inv.amount) *p(daily_percentage)
#                 print(ur_daily_earning)

#                 nos_days_earned = (set_date  -  today).days
#                 print(nos_days_earned)

#                 extra_profit = int(ur_daily_earning * nos_days_earned)
#                 print(f"extra profit is {extra_profit}")

#                 total_roi = user_earning.amount + extra_profit
#                 print(f"total ROI is {total_roi}")
                
            
#                 data['Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                 data['Invested_Amount'].append(f"{inv.amount}")
#                 data['ROI'].append(f"{total_roi}")
#                 data['Account_Number'].append(user_account.account_number)
#                 data['Bank'].append(user_account.bank_name)
#                 if user_profile.remit_inv_funds_to_wallet == True:
#                     data['Payment_Preference'].append('Pay To Wallet')
#                 else:
#                     data['Payment_Preference'].append('Pay To Bank Account')
#             else:
#                 pass
               
#         else:
#             print(f"error with {user_profile.user.email} payout date")
#             print(f"error with {inv.txn_code}")


           
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     new_df.to_excel(f"cip_investment_roi_payouts_real_{set_date}.xlsx", index = False, header=True)
#     #new_df.to_excel(f"cip_investment_roi_payouts_migrated_{set_date}.xlsx", index = False, header=True)

#     context = {
#             'the_data':data
#         }
   
#     # response = JsonResponse(data)
#     # return response
#     return render(request, template, context)



# This is for migrated users
# def get_cip_payout(request):
#     data_col = ['Name', 'Invested_Amount',  'ROI', 'Account_Number', 'Bank', 'Payment_Preference']
#     data = {
#             'Name':[], 'Invested_Amount':[], 'ROI':[], 'Account_Number':[], 'Bank':[], 'Payment_Preference':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     today = datetime.date(datetime.astimezone(datetime.today()))
#     set_date_str = '01/03/21 00:00:00'
#     set_date = datetime.strptime(set_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(f"Set date is {set_date}")
#     #cip_investments = UserInvestment.objects.filter(active=True,cip_pioneer=False,hip_pioneer=False).all()
#     cip_investments = UserInvestment.objects.filter(active=True,cip_pioneer=True,completed=False).all()
#     for inv in cip_investments:
        
        
#         if inv.next_payout:
#             user_profile = inv.user     
#             if  inv.next_payout.date() == set_date:
#                 user_account = UserBankAccount.objects.filter(user=user_profile).first()
#                 user_earning = UserInvestmentEarnings.objects.filter(user=user_profile,plan=inv).first()
#                 print(f"Data is here for user {inv.user.user.email}")
#                 print(f"Investment amount is {inv.amount}")


#                 print(f"Investment Earning now is {user_earning.amount}")

#                 # print(f"Investment Profit Earned is {inv.profit_earned}")



                
#                 p = lambda x: x/100
#                 daily_percentage = (inv.plan.percentage_interest) / 30 
#                 print(daily_percentage) 
#                 ur_daily_earning = float(inv.amount) *p(daily_percentage)
#                 print(ur_daily_earning)

#                 nos_days_earned = (set_date  -  today).days
#                 print(nos_days_earned)

#                 extra_profit = int(ur_daily_earning * nos_days_earned)
#                 print(f"extra profit is {extra_profit}")

#                 total_roi_fake = user_earning.amount + extra_profit
#                 print(f"total ROI is {total_roi_fake}")

#                 total_roi = int(ur_daily_earning * 30)
#                 print(f"ROI should be {total_roi}")
                
#                 # user_earning.amount = total_roi
#                 # user_earning.save()

#                 data['Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                 data['Invested_Amount'].append(f"{inv.amount}")
#                 data['ROI'].append(f"{total_roi}")
#                 data['Account_Number'].append(user_account.account_number)
#                 data['Bank'].append(user_account.bank_name)
#                 if user_profile.remit_inv_funds_to_wallet == True:
#                     data['Payment_Preference'].append('Pay To Wallet')
#                 else:
#                     data['Payment_Preference'].append('Pay To Bank Account')
#             else:
#                 pass
               
#         else:
#             print(f"error with {user_profile.user.email} payout date")
#             print(f"error with {inv.txn_code}")


           
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     #new_df.to_excel(f"cip_investment_roi_payouts_real_{set_date}.xlsx", index = False, header=True)
#     new_df.to_excel(f"cip_investment_roi_payouts_migrated_{set_date}.xlsx", index = False, header=True)

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)



# def get_toped_up_inv_with_sponsors(request):
#     data_col = ['Investor_Name', 'Investor_Email',  'Invested_Amount', 'Top_Up_Date' ,'Top_Up_Amount', 'New_Investment_Capital', 'Investment_Type',  'Investment_Started_Date', 'Sponsor_Name', 'Sponsor_Email', 'Sponsor_Account_Number', 'Sponsor_Bank_Name', 'Sponsor_Account_Name']
#     data = {
#             'Investor_Name':[],'Investor_Email':[], 'Invested_Amount':[], 'Top_Up_Date':[] , 'Top_Up_Amount':[], 'New_Investment_Capital':[],  'Investment_Type':[], 'Investment_Started_Date':[], 'Sponsor_Name':[], 'Sponsor_Email':[], 'Sponsor_Account_Number':[], 'Sponsor_Bank_Name':[], 'Sponsor_Account_Name':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     start_date_str = '01/03/21 00:00:00'
#     end_date_str = '31/03/21 00:00:00'
#     start_date = datetime.strptime(start_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(start_date)
#     end_date = datetime.strptime(end_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(end_date)
#     top_ups = UserInvestmentTopups.objects.all()
#     for tp in top_ups:
#         user_profile = tp.user
#         the_inv = tp.investment
#         if the_inv.cip_pioneer == False and the_inv.hip_pioneer == False and the_inv.active == True and the_inv.completed == False:
#             if tp.created_at.date() >= start_date and tp.created_at.date() <= end_date:
#                 print("Data is here!")
#                 print(f"Top up amount is {tp.amount}")

#                 check_downline = UserReferrals.objects.filter(downline=user_profile)
#                 if check_downline.exists(): 
#                     the_downline = check_downline.first()
#                     sponsor = the_downline.sponsor

#                     data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                     data['Investor_Email'].append(f"{user_profile.user.email}")
#                     data['New_Investment_Capital'].append(the_inv.amount)
#                     data['Investment_Type'].append(f"{the_inv.plan.category.name}")
#                     data['Investment_Started_Date'].append(f"{the_inv.created_at.date()}")

#                     data['Invested_Amount'].append(f"{int(the_inv.amount) - int(tp.amount)}")
#                     data['Top_Up_Amount'].append(f"{int(tp.amount)}")
#                     data['Top_Up_Date'].append(f"{tp.created_at.date()}")

                    




#                     data['Sponsor_Name'].append(f"{sponsor.first_name} {sponsor.last_name}")
#                     data['Sponsor_Email'].append(f"{sponsor.user.email}")

#                     sponsor_acct_det = UserBankAccount.objects.filter(user=sponsor).first()

#                     data['Sponsor_Account_Number'].append(f"{sponsor_acct_det.account_number}")
#                     data['Sponsor_Bank_Name'].append(f"{sponsor_acct_det.bank_name}")
#                     data['Sponsor_Account_Name'].append(f"{sponsor_acct_det.account_name}")

#                 else:
#                     print(f"User {user_profile} does not have a sponsor, move on ")
#         else:
#             print("Investment record not in time frame")
            

#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     new_df.to_excel(f"top_ups_with_sponsors_{start_date}_to_{end_date}.xlsx")

#     context = {
#             'the_data':data
#         }
    
#     return render(request, template, context)


# def get_cip_payoutttt(request):
#     data_col = ['Investor_Name', 'Investor_Email',  'Invested_Amount', 'Investment_Type',  'Investment_Started_Date', 'Sponsor_Name', 'Sponsor_Email', 'Sponsor_Account_Number', 'Sponsor_Bank_Name', 'Sponsor_Account_Name']
#     data = {
#             'Investor_Name':[],'Investor_Email':[], 'Invested_Amount':[],   'Investment_Type':[], 'Investment_Started_Date':[], 'Sponsor_Name':[], 'Sponsor_Email':[], 'Sponsor_Account_Number':[], 'Sponsor_Bank_Name':[], 'Sponsor_Account_Name':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     start_date_str = '01/03/21 00:00:00'
#     end_date_str = '15/03/21 00:00:00'
#     start_date = datetime.strptime(start_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(start_date)
#     end_date = datetime.strptime(end_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(end_date)
#     cip_investments = UserInvestment.objects.filter(cip_pioneer=False, hip_pioneer=False, active=True).all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         if inv.created_at.date() >= start_date and inv.created_at.date() <= end_date:
#             print("Data is here!")
#             print(f"Investment amount is {inv.amount}")

#             check_downline = UserReferrals.objects.filter(downline=user_profile)
#             if check_downline.exists():
                    
#                 the_downline = check_downline.first()
#                 sponsor = the_downline.sponsor

#                 data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                 data['Investor_Email'].append(f"{user_profile.user.email}")
#                 data['Invested_Amount'].append(inv.amount)
#                 data['Investment_Type'].append(f"{inv.plan.category.name}")
#                 data['Investment_Started_Date'].append(f"{inv.created_at.date()}")

                




#                 data['Sponsor_Name'].append(f"{sponsor.first_name} {sponsor.last_name}")
#                 data['Sponsor_Email'].append(f"{sponsor.user.email}")

#                 sponsor_acct_det = UserBankAccount.objects.filter(user=sponsor).first()

#                 data['Sponsor_Account_Number'].append(f"{sponsor_acct_det.account_number}")
#                 data['Sponsor_Bank_Name'].append(f"{sponsor_acct_det.bank_name}")
#                 data['Sponsor_Account_Name'].append(f"{sponsor_acct_det.account_name}")
#             else:
#                 print(f"User {user_profile} does not have a sponsor, move on ")
            
#         else:
#             print("Investment record not in time frame")
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     new_df.to_excel(f"new_investment_records_with_sponsors_{start_date}_to_{end_date}.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)



# def get_cip_inv_that_topedup_and_have_sponsors(request):
#     data_col = ['Investor_Name', 'Investor_Email',  'Invested_Amount', 'Total_Top_Up_Amount', 'New_Investment_Capital', 'Investment_Type',  'Investment_Started_Date', 'Sponsor_Name', 'Sponsor_Email', 'Sponsor_Account_Number', 'Sponsor_Bank_Name', 'Sponsor_Account_Name']
#     data = {
#             'Investor_Name':[],'Investor_Email':[], 'Invested_Amount':[], 'Total_Top_Up_Amount':[], 'New_Investment_Capital':[],  'Investment_Type':[], 'Investment_Started_Date':[], 'Sponsor_Name':[], 'Sponsor_Email':[], 'Sponsor_Account_Number':[], 'Sponsor_Bank_Name':[], 'Sponsor_Account_Name':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     start_date_str = '01/03/21 00:00:00'
#     end_date_str = '31/03/21 00:00:00'
#     start_date = datetime.strptime(start_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(start_date)
#     end_date = datetime.strptime(end_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(end_date)
#     cip_investments = UserInvestment.objects.filter(cip_pioneer=False, hip_pioneer=False, active=True).all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         if inv.created_at.date() >= start_date and inv.created_at.date() <= end_date:
#             print("Data is here!")
#             print(f"Investment amount is {inv.amount}")

#             check_downline = UserReferrals.objects.filter(downline=user_profile)
#             if check_downline.exists():
#                 check_if_user_top_up = UserInvestmentTopups.objects.filter(user=user_profile, investment=inv)
#                 if check_if_user_top_up.exists():

#                     sum_top_up = check_if_user_top_up.aggregate(amount_sum=Sum("amount"))
#                     print(sum_top_up['amount_sum'])
#                     the_downline = check_downline.first()
#                     sponsor = the_downline.sponsor

#                     data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                     data['Investor_Email'].append(f"{user_profile.user.email}")
#                     data['New_Investment_Capital'].append(inv.amount)
#                     data['Investment_Type'].append(f"{inv.plan.category.name}")
#                     data['Investment_Started_Date'].append(f"{inv.created_at.date()}")

#                     data['Invested_Amount'].append(f"{int(inv.amount) - int(sum_top_up['amount_sum'])}")
#                     data['Total_Top_Up_Amount'].append(f"{int(sum_top_up['amount_sum'])}")




#                     data['Sponsor_Name'].append(f"{sponsor.first_name} {sponsor.last_name}")
#                     data['Sponsor_Email'].append(f"{sponsor.user.email}")

#                     sponsor_acct_det = UserBankAccount.objects.filter(user=sponsor).first()

#                     data['Sponsor_Account_Number'].append(f"{sponsor_acct_det.account_number}")
#                     data['Sponsor_Bank_Name'].append(f"{sponsor_acct_det.bank_name}")
#                     data['Sponsor_Account_Name'].append(f"{sponsor_acct_det.account_name}")
#             else:
#                 print(f"User {user_profile} does not have a sponsor, move on ")
            
#         else:
#             print("Investment record not in time frame")
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     new_df.to_excel(f"investment_records_for_sponsors_with_top_up_{start_date}_to_{end_date}.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)




# def get_rolled_over_inv_with_sponsors(request):
#     data_col = ['Investor_Name', 'Investor_Email',  'Invested_Amount',  'Investment_Type',  'Investment_Started_Date', 'Sponsor_Name', 'Sponsor_Email', 'Sponsor_Account_Number', 'Sponsor_Bank_Name', 'Sponsor_Account_Name']
#     data = {
#             'Investor_Name':[],'Investor_Email':[], 'Invested_Amount':[],  'Investment_Type':[], 'Investment_Started_Date':[], 'Sponsor_Name':[], 'Sponsor_Email':[], 'Sponsor_Account_Number':[], 'Sponsor_Bank_Name':[], 'Sponsor_Account_Name':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     start_date_str = '01/03/21 00:00:00'
#     end_date_str = '15/03/21 00:00:00'
#     start_date = datetime.strptime(start_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(start_date)
#     end_date = datetime.strptime(end_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(end_date)
#     cip_investments = UserInvestment.objects.filter(cip_pioneer=False, hip_pioneer=False, active=True).all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         if inv.created_at.date() >= start_date and inv.created_at.date() <= end_date:
#             print("Data is here!")
#             print(f"Investment amount is {inv.amount}")

#             check_downline = UserReferrals.objects.filter(downline=user_profile)
#             if check_downline.exists():
#                 check_if_rollover = UserInvestmentRollovers.objects.filter(user=user_profile, new_investment=inv)
#                 if check_if_rollover.exists():

                    
#                     the_downline = check_downline.first()
#                     sponsor = the_downline.sponsor

#                     data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                     data['Investor_Email'].append(f"{user_profile.user.email}")
                   
#                     data['Investment_Type'].append(f"{inv.plan.category.name}")
#                     data['Investment_Started_Date'].append(f"{inv.created_at.date()}")

#                     data['Invested_Amount'].append(f"{int(inv.amount)}")
                




#                     data['Sponsor_Name'].append(f"{sponsor.first_name} {sponsor.last_name}")
#                     data['Sponsor_Email'].append(f"{sponsor.user.email}")

#                     sponsor_acct_det = UserBankAccount.objects.filter(user=sponsor).first()

#                     data['Sponsor_Account_Number'].append(f"{sponsor_acct_det.account_number}")
#                     data['Sponsor_Bank_Name'].append(f"{sponsor_acct_det.bank_name}")
#                     data['Sponsor_Account_Name'].append(f"{sponsor_acct_det.account_name}")
#             else:
#                 print(f"User {user_profile} does not have a sponsor, move on ")
            
#         else:
#             print("Investment record not in time frame")
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     new_df.to_excel(f"rolled_over_investments_with_sponsors_{start_date}_to_{end_date}.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)




# def get_cip_payout(request):
#     data_col = ['User_Full_Name', 'User_Email', 'User_Phone', 'User_Account_Number', 'User_Bank_Name', 'User_Account_Name']
#     data = {
#             'User_Full_Name':[],'User_Email':[], 'User_Phone':[], 'User_Account_Number':[], 'User_Bank_Name':[], 'User_Account_Name':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'

#     profiles = UserInvestment.objects.filter(cip_pioneer=True).all()
#     for inv in profiles:
#         user = inv.user
#         print(f"User {user.user.email} available")
#         data['User_Full_Name'].append(f"{user.first_name} {user.last_name}")
#         data['User_Email'].append(f"{user.user.email}")
#         data['User_Phone'].append(user.phone)

     

#         user_acct_det = UserBankAccount.objects.filter(user=user).first()

#         data['User_Account_Number'].append(f"{user_acct_det.account_number}")
#         data['User_Bank_Name'].append(f"{user_acct_det.bank_name}")
#         data['User_Account_Name'].append(f"{user_acct_det.account_name}")
       
            
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     # new_df.to_excel(f"all_partner_details.xlsx")
#     new_df.to_excel(f"all_cip_details_1.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)


# def get_cip_payout(request):
#     data_col = ['Investment_Txn', 'Investment_ID', 'User_Email','User_FullName', 'Investment_Started', 'Investment_Amount','Next_Payout', 'CIP_Piooner']
#     data = {
#             'Investment_Txn':[], 'Investment_ID':[], 'User_Email':[],'User_FullName':[], 'Investment_Started':[], 'Investment_Amount':[], 'Next_Payout':[], 'CIP_Piooner':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'

#     today = datetime.today()
#     print(today)
#     set_date = datetime.date(today)
#     next_pay_date_str = '15/03/21 00:00:00'
#     nxt_pay = datetime.strptime(next_pay_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(set_date)
#     profiles = UserInvestment.objects.filter(active=True).all()
#     for inv in profiles:
#         user = inv.user
#         if inv.mig_modified.date() == set_date and inv.next_payout.date() != nxt_pay:
#             print(f"User {user.user.email} available")
#             data['User_Email'].append(f"{user.user.email}")
#             data['User_FullName'].append(f"{user.first_name} {user.last_name}")
#             data['Investment_Started'].append(f"{inv.created_at.date()}")
#             data['Investment_Amount'].append(f"{inv.amount}")
#             data['Next_Payout'].append(f"{inv.next_payout.date()}")
#             data['CIP_Piooner'].append(f"{inv.cip_pioneer}")

#             data['Investment_Txn'].append(f"{inv.txn_code}")
#             data['Investment_ID'].append(f"{inv.pk}")


     
       
            
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     # new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     # new_df.to_excel(f"all_partner_details.xlsx")
#     new_df.to_excel(f"modified_today.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)



# class CreditMissedPayouts(View):

#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)

#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)

#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
#                 print(the_doc.doc)
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()


                
#                 p = lambda x: x/100
#                 today = datetime.now()
#                 today = pytz.utc.localize(today)

#                 transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))

#                 for index, row in the_import.iterrows():

                    
                    
                   
                   
#                     print(row['user_email'])
#                     the_email =  str(row['user_email']).lower().strip()
#                     print(the_email)
                    
#                     the_user = User.objects.get(email=the_email)
#                     user_profile = the_user.profile
#                     print(user_profile.first_name)

#                     the_tnx_code = row['investment_txn']
#                     the_pk = row['investment_id']

#                     investment = UserInvestment.objects.get(pk=the_pk)

#                     investment_earning = UserInvestmentEarnings.objects.get(plan=investment, active=True, completed=False)

#                     amount = investment.amount
#                     plan = investment.plan
#                     percentage = plan.percentage_interest
#                     maturity_date = investment.maturity_date
#                     created_date = investment.created_at
#                     next_payout = investment.next_payout
#                     daily_percentage = int(percentage) / 30 
#                     earning = float(amount) *p(daily_percentage)



#                     print("User is to be paid into their bank account")
#                     payout_this_month = investment_earning.amount

#                     new_payment = Payments.objects.create(txn_code=transaction_code, amount=payout_this_month, user = investment_earning.user, destination="bank_account", status='pending',remark=f"CIP ROI Payout for {investment_earning.plan.txn_code} - {investment_earning.plan.display_name}")

#                     new_roi_tnx = Transaction.objects.create(amount=investment_earning.amount, txn_code=transaction_code, user = investment_earning.user, txn_method="manual", txn_type='investment_earnings')

#                     investment_earning.plan.profit_earned += earning
#                     investment_earning.plan.profit_paid += payout_this_month

                    

#                     investment_earning.amount = earning
#                     investment_earning.save()
#                     investment_earning.plan.next_payout = today + timedelta(30)
#                     investment_earning.plan.save()


#                     print(f"Done with {investment_earning.user.user.email}")







                    

                   

                        
                 
                    
                    
#                 print("All records treated ")
                 


#             return HttpResponseRedirect(reverse("users:credit-missed-payout"))

                    
        
#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:credit-missed-payout"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:credit-missed-payout"))



# def get_cip_payout(request):
#     data_col = ['Investor_Name', 'Investor_Email',  'Invested_Amount', 'Investment_Started_Date', 'Old_Investment_Next_Payout', 'New_Investment_Next_Payout' ]
#     data = {
#             'Investor_Name':[],'Investor_Email':[], 'Invested_Amount':[], 'Investment_Started_Date':[], 'Old_Investment_Next_Payout':[], 'New_Investment_Next_Payout':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     start_date_str = '11/02/21 00:00:00'

#     start_date = datetime.strptime(start_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(start_date)
 
#     cip_investments = UserInvestment.objects.filter(completed=False, active=True).all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         if inv.next_payout.date() <= start_date:
#             print("Data is here!")
#             print(f"Investment amount is {inv.amount}")


#             data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#             data['Investor_Email'].append(f"{user_profile.user.email}")
#             data['Invested_Amount'].append(inv.amount)
#             data['Investment_Started_Date'].append(f"{inv.created_at.date()}")
#             data['Old_Investment_Next_Payout'].append(f"{inv.next_payout.date()}")

#             inv.next_payout += timedelta(days=30)

#             inv.save()

#             data['New_Investment_Next_Payout'].append(f"{inv.next_payout.date()}")



        
            
#         else:
#             print("Investment record not in time frame")
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     new_df.to_excel(f"missed_payout_records_real_1.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)



# def get_specific_investment_type_by_date(request):
#     data_col = ['Investor_Name', 'Investor_Address', 'Investor_Email',  'Invested_Amount', 'Investment_Duration', 'Investment_Started_Date', 'Investment_Plan_Type']
#     data = {
#             'Investor_Name':[], 'Investor_Address':[], 'Investor_Email':[], 'Invested_Amount':[], 'Investment_Duration':[], 'Investment_Started_Date':[], 'Investment_Plan_Type':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     # start_date_str = '01/01/21 00:00:00'
#     # end_date_str = '16/03/21 00:00:00'
#     # start_date = datetime.strptime(start_date_str, '%d/%m/%y %H:%M:%S').date()
#     # print(start_date)
#     # end_date = datetime.strptime(end_date_str, '%d/%m/%y %H:%M:%S').date()
#     # print(end_date)
#     cip_investments = UserInvestment.objects.filter(plan__category__name="HIP", active=True, completed=False).all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         # if inv.created_at.date() >= start_date and inv.created_at.date() <= end_date:
#         print("Data is here!")
#         print(f"Investment amount is {inv.amount}")

        
#         data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#         data['Investor_Address'].append(f"{user_profile.address_1} - {user_profile.address_2} - {user_profile.city} - {user_profile.state} - {user_profile.nationality}")
#         data['Investor_Email'].append(f"{user_profile.user.email}")
#         data['Invested_Amount'].append(inv.amount)
#         data['Investment_Duration'].append(f"{int(int(inv.maturity_days)/30)}")
#         data['Investment_Started_Date'].append(f"{inv.created_at.date()}")
#         data['Investment_Plan_Type'].append(f"{inv.plan.category.name}")

                
           
            
#         # else:
#         #     print("Investment record not in time frame")
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     #new_df.to_excel(f"all_investments_{start_date}_to_{end_date}.xlsx")
#     new_df.to_excel(f"all_hip_investments_done_on_the_app.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)


# def get_total_uninvested_wallet(request):

    # unused_dep = MainWallet.objects.all().aggregate(deposit_sum=Sum("deposit"))
    # unused = unused_dep['deposit_sum']
    # print(unused)

    # unused_deps = MainWallet.objects.filter(deposit__gte=50000).all()
    # for user in unused_deps:
    #     print(f"{user.user.user.email} has {user.deposit}")

    # double_sponsors = UserReferrals.objects.all()
    # for prof in double_sponsors:
    #     downlines = prof.downline
    #     print(f"{prof.sponsor.user.email} refered {prof.downline.user.email} " )
        # if downlines > 2:
        #     print('YES')
        #     print(f"{prof.sponsor.user.email} refered {prof.downline.user.email} " )
    
    # for prof in double_sponsors:
    #     if prof.sponsor.count() > 1:
    #         print("YES")
    #         print(prof.downline.user.user.email)
    #         print(prof.sponsor.user.user.email)
    #     else:
    #         pass


    # approved_dep = Deposit.objects.filter(approved=True).all().aggregate(approved_sum=Sum("amount"))
    # approved = approved_dep['approved_sum']
    # print(approved)

    # user_inv = UserInvestment.objects.filter(active=True, completed=False).aggregate(amount_sum=Sum("amount"))
    # invested = user_inv['amount_sum']
    # print(invested)


    # user_inv = UserInvestment.objects.filter(active=True, amount__lt = int(300000), completed=False).all()
    
    # under_50k = user_inv.count()
    # for inv in user_inv:
    #     print(f"{inv.user.user.email}  - {inv.amount}")
    # print(under_50k)
    # user_inv = UserInvestment.objects.filter(active=True, amount__lt = int(300000), completed=False).aggregate(amount_sum=Sum("amount"))
    # invested = user_inv['amount_sum']
    # print(invested)
    
    # old_cip = UserInvestment.objects.filter(plan__category__name="CIP", plan__name="Plan A", active=True).all()
    # print(old_cip)
    # for inv in old_cip:
    #     if inv.can_top_up == True:
    #         print(f"started with {inv.user.user.email} ")
    #         inv.can_top_up = False
    #         inv.save()
    #         print(f"done with {inv.user.user.email} ")

    # return redirect('/')



# class ImportTopUps(View):

#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)

#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)

#         try:
#             data_col = ['Investor_Email',  'Invested_Amount',  'Investment_Started_Date', 'Old_Capital', 'Last_Payout', 'Old_Daily_Earning', 'Next_Payout', 'Set_Top_Up_Date', 'New_Capital', 'New_Daily_Earning', 'No_of_Days_After_Topup', 'Total_ROI_Before_Topup', 'Total_ROI_After_Topup', 'Has_Done_Top_Up_Before' ]
#             data = {
#                     'Investor_Email':[], 'Invested_Amount':[], 'Investment_Started_Date':[], 'Old_Capital':[], 'Last_Payout':[], 'Old_Daily_Earning':[], 'Next_Payout':[], 'Set_Top_Up_Date':[], 'New_Capital':[], 'New_Daily_Earning':[], 'No_of_Days_After_Topup':[], 'Total_ROI_Before_Topup':[] ,'Total_ROI_After_Topup':[], 'Has_Done_Top_Up_Before':[]
#                                 }
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
#                 print(the_doc.doc)
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 feb_date_str = '02/03/21 00:00:00'
#                 feb_date = datetime.strptime(feb_date_str, '%d/%m/%y %H:%M:%S').date()
                
#                 p = lambda x: x/100
#                 today = datetime.date(datetime.astimezone(datetime.today()))

#                 transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))

#                 for index, row in the_import.iterrows():

                    
                    
#                     the_top_up_amount = int(row['top up amount'])
#                     print(f"the top up amount is {the_top_up_amount}")
                   
                  
#                     the_email =  str(row['email address']).lower().strip()
#                     print(f"the user email is {the_email}")
                    
#                     the_user = User.objects.get(email=the_email)
#                     user_profile = the_user.profile
#                     print(f" the user first name is {user_profile.first_name}")


#                     investment = UserInvestment.objects.filter(user=user_profile, completed=False,active=True).first()
#                     if investment:
#                         # if investment.get_last_payout.month == feb_date.month:
#                         #     print("Investment is in Feb")

#                         print(f"old invested capital is {investment.amount}")
#                         print(f" investment created at {investment.created_at}")
#                         print(f"the next payout is {investment.next_payout}")
#                         print(f" the last payout was {investment.get_last_payout}")

#                         data['Investor_Email'].append(f"{user_profile.user.email}")
#                         data['Invested_Amount'].append(f"{investment.amount}")
#                         data['Investment_Started_Date'].append(f"{investment.created_at.date()}")
#                         data['Old_Capital'].append(f"{investment.amount}")
#                         data['Last_Payout'].append(f"{investment.get_last_payout}")
                        
#                         data['Next_Payout'].append(f"{investment.next_payout.date()}")

#                         user_did_topup = investment.user_investment_topup
#                         if user_did_topup.exists():
#                             data['Has_Done_Top_Up_Before'].append(f"YES")
#                         else:
#                             data['Has_Done_Top_Up_Before'].append(f"NO")
                        

                        
                        
                        
                        
                        


#                         investment_earning = UserInvestmentEarnings.objects.get(plan=investment, active=True, completed=False)
#                         print(investment_earning.amount)


                        
#                         # set_top_up_date_str = '07/02/21 00:00:00'
#                         # set_top_up_date = datetime.strptime(set_top_up_date_str, '%d/%m/%y %H:%M:%S').date()
#                         # set_top_up_datetime = datetime.strptime(set_top_up_date_str, '%d/%m/%y %H:%M:%S')
#                         # print(f"top up datetime is {set_top_up_datetime} and make aware is {make_aware(set_top_up_datetime)} ")
#                         set_top_up_datetime = investment.get_last_payout + timedelta(days=1)
#                         set_top_up_date = datetime.date(set_top_up_datetime)
#                         print(f"top up datetime is {set_top_up_datetime} and date {set_top_up_date} ")
#                         data['Set_Top_Up_Date'].append(f"{set_top_up_date}")

                        




#                         old_capital = investment.amount
#                         plan = investment.plan
#                         percentage = plan.percentage_interest
#                         maturity_date = investment.maturity_date
#                         created_date = investment.created_at
#                         next_payout = investment.next_payout
#                         daily_percentage = int(percentage) / 30 
#                         earning = float(old_capital) *p(daily_percentage)
#                         print(f" old earning power is {earning}")
#                         data['Old_Daily_Earning'].append(f"{earning}")

#                         if investment.get_last_payout.date() < today:
#                             nos_days_before_top_up = (set_top_up_date  -  investment.get_last_payout.date()).days
#                             print(f"number of days before topup is {nos_days_before_top_up}")

#                             earning_before_top_up = int(earning * nos_days_before_top_up)
#                             print(f" total earnings before top up is  {earning_before_top_up}")

#                             #Process Top Up 

#                             # new_top_up, created = UserInvestmentTopups.objects.get_or_create(investment=investment, user=user_profile, created_at = set_top_up_datetime, amount=the_top_up_amount)

#                             # investment.amount += new_top_up.amount
#                             # investment.save()
    
#                             new_capital = int(investment.amount + the_top_up_amount)
#                             print(f"new capital is {new_capital}")
#                             data['New_Capital'].append(f"{new_capital}")

#                             the_inv_earning = UserInvestmentEarnings.objects.get(plan=investment, user=user_profile)

#                             print(f"total earnings before {the_inv_earning.amount}")
#                             data['Total_ROI_Before_Topup'].append(f"{the_inv_earning.amount}")

#                             new_earning = float(new_capital) *p(daily_percentage)
#                             print(f"new earning power is {new_earning}")
#                             data['New_Daily_Earning'].append(f"{new_earning}")

                            
                            

#                             nos_days_after_top_up = (today  -  set_top_up_date).days
#                             print(f"number of days after top up is {nos_days_after_top_up}")
#                             data['No_of_Days_After_Topup'].append(f"{nos_days_after_top_up}")


#                             earning_after_top_up = int(new_earning * nos_days_after_top_up)
#                             print(f" total earnings till now after top up is  {earning_after_top_up}")
#                             data['Total_ROI_After_Topup'].append(f"{earning_after_top_up}")

#                             # total_roi = earning_after_top_up

#                             # the_inv_earning.amount = total_roi
#                             # the_inv_earning.save()
#                             total_roi = earning_after_top_up + earning_before_top_up
#                             print(f"total roi as of today is {total_roi}")


#                             print(f"Done with {user_profile.user.email}")
#                     else:
#                         print(f"{user_profile.user.email} has no investment ")
                 
                    
                   
#                 print("All records treated ")
                 

#             print(data)
#             new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#             new_df = new_df.drop_duplicates(keep = False, inplace = False)
#             # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#             #new_df.to_excel(f"all_investments_{start_date}_to_{end_date}.xlsx")
#             new_df.to_excel(f"test_topup_analysis.xlsx")

#             return HttpResponseRedirect(reverse("users:import_top_ups"))

                    
        
#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:import_top_ups"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:import_top_ups"))



# class TopupBalance(View):


#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)

#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)

#         try:
            
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
#                 print(the_doc.doc)
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

                
#                 p = lambda x: x/100
#                 today = datetime.date(datetime.astimezone(datetime.today()))

#                 transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))

#                 for index, row in the_import.iterrows():

#                     print("This is a top up balance")
                    
#                     the_top_up_amount = int(row['top up amount'])
#                     print(f"the top up amount is {the_top_up_amount}")
                   
                  
#                     the_email =  str(row['email address']).lower().strip()
#                     print(f"the user email is {the_email}")
                    
#                     the_user = User.objects.get(email=the_email)
#                     user_profile = the_user.profile
#                     print(f" the user first name is {user_profile.first_name}")


#                     investment = UserInvestment.objects.filter(user=user_profile, completed=False,active=True).first()
#                     if investment:
#                         print(f"old invested capital is {investment.amount}")
#                         print(f" investment created at {investment.created_at}")
#                         print(f"the next payout is {investment.next_payout}")
#                         print(f" the last payout was {investment.get_last_payout}")

                        
                        
                        
                        


#                         investment_earning = UserInvestmentEarnings.objects.get(plan=investment, active=True, completed=False, user=user_profile)
#                         print(investment_earning.amount)


#                         set_top_up_datetime = investment.get_last_payout + timedelta(days=1)
#                         set_top_up_date = (investment.get_last_payout + timedelta(days=1))
#                         print(f"top up datetime is {set_top_up_datetime} and date {set_top_up_date} ")
            

                        




#                         old_capital = investment.amount
#                         plan = investment.plan
#                         percentage = plan.percentage_interest
#                         maturity_date = investment.maturity_date
#                         created_date = investment.created_at
#                         next_payout = investment.next_payout
#                         daily_percentage = int(percentage) / 30 
#                         earning = float(old_capital) *p(daily_percentage)
#                         print(f" old earning power is {earning}")
                        
#                         print(f" total earnings before top up is  {investment_earning.amount}")

#                         #Process Top Up 

#                         new_top_up, created = UserInvestmentTopups.objects.get_or_create(investment=investment, user=user_profile, created_at = set_top_up_datetime, amount=the_top_up_amount)

#                         investment.amount += new_top_up.amount
#                         investment.save()

#                         new_capital = int(investment.amount + the_top_up_amount)
#                         print(f"new capital is {new_capital}")
                     

                     
                   

#                         new_earning = float(new_capital) *p(daily_percentage)
#                         print(f"new earning power is {new_earning}")


                        
                        

#                         nos_days_after_top_up = (today  -  investment.get_last_payout).days
#                         print(f"number of days after top up is {nos_days_after_top_up}")
  


#                         earning_after_top_up = int(new_earning * nos_days_after_top_up)
#                         print(f"total earnings till now after top up is  {earning_after_top_up}")


#                         total_roi = earning_after_top_up

#                         investment_earning.amount = total_roi
#                         investment_earning.save()

#                         investment.profit_earned = investment.profit_paid + total_roi
#                         investment.mig_batch = f"seven(toped up on {today})"
#                         investment.save()
                    


#                         print(f"Done with {user_profile.user.email}")
#                     else:
#                         print(f"{user_profile.user.email} has no investment ")
                 
                    
                   
#                 print("All records treated ")
                 

        

#             return HttpResponseRedirect(reverse("users:top_up_balance"))

                    
        
#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:top_up_balance"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:top_up_balance"))


    

    


# #This is to correct user records 
# def get_cip_payoutttt(request):
#     data_col = ['Name', 'Invested_Amount',  'Total_Earning_Now', 'Correct_Earning_Now', 'Total_ROI_On_PayDay',]
#     data = {
#             'Name':[], 'Invested_Amount':[], 'Total_Earning_Now':[], 'Correct_Earning_Now':[], 'Total_ROI_On_PayDay':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     today = datetime.date(datetime.astimezone(datetime.today()))
#     print(today)
#     set_date_str = '31/03/21 00:00:00'
#     set_date = datetime.strptime(set_date_str, '%d/%m/%y %H:%M:%S').date()
#     print(f"Set date is {set_date}")
#     #cip_investments = UserInvestment.objects.filter(active=True,cip_pioneer=False,hip_pioneer=False).all()
#     cip_investments = UserInvestment.objects.filter(active=True, plan__category__name="CIP", completed=False).all()
#     for inv in cip_investments:
#         top_up = inv.user_investment_topup
#         if not top_up.exists():
#             if inv.next_payout:
#                 user_profile = inv.user     
#                 if  inv.next_payout.date() == set_date:
#                     user_account = UserBankAccount.objects.filter(user=user_profile).first()
#                     user_earning = UserInvestmentEarnings.objects.filter(user=user_profile,plan=inv).first()
#                     print(f"Data is here for user {inv.user.user.email}")
#                     print(f"Investment amount is {inv.amount}")


#                     print(f"Investment Earning now is {user_earning.amount}")
#                     data['Total_Earning_Now'].append(f"{user_earning.amount}")

#                     # print(f"Investment Profit Earned is {inv.profit_earned}")



                    
#                     p = lambda x: x/100
#                     daily_percentage = (inv.plan.percentage_interest) / 30 
#                     print(daily_percentage) 
#                     ur_daily_earning = float(inv.amount) *p(daily_percentage)
#                     print(ur_daily_earning)

#                     nos_days_earned = (set_date  -  today).days
#                     print(nos_days_earned)

#                     extra_profit = int(ur_daily_earning * nos_days_earned)
#                     print(f"extra profit is {extra_profit}")

#                     # total_roi_fake = user_earning.amount + extra_profit
#                     # print(f"total ROI is {total_roi_fake}")

#                     # total_roi = int(ur_daily_earning * 29)
#                     # print(f"ROI should be {total_roi}")

#                     total_roi_payday = int(ur_daily_earning * 30)
#                     print(f"ROI on Payday should be {total_roi_payday}")


#                     total_roi = int(ur_daily_earning * 30)
#                     print(f"Earning now should be {total_roi}")

                    


                    
#                     # user_earning.amount = total_roi
#                     # user_earning.save()

#                     data['Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                     data['Invested_Amount'].append(f"{inv.amount}")
                    
#                     data['Correct_Earning_Now'].append(f"{total_roi}")
#                     data['Total_ROI_On_PayDay'].append(f"{total_roi_payday}")
                    
#                 else:
#                     pass
                
#             else:
#                 print(f"error with {user_profile.user.email} payout date")
#                 print(f"error with {inv.txn_code}")
#         else:
#             print(f"{inv.user} has done topup before")

           
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     #new_df.to_excel(f"cip_investment_roi_payouts_real_{set_date}.xlsx", index = False, header=True)
#     new_df.to_excel(f"correcting_investment_earnings_{set_date}.xlsx", index = False, header=True)

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)



# def get_all_paytowallet(request):
#     data_col = ['First_Name', 'Last_Name',  'Email', 'Phone_Number',]
#     data = {
#             'First_Name':[], 'Last_Name':[], 'Email':[], 'Phone_Number':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'

#     all_the_profile = Profile.objects.filter(remit_inv_funds_to_wallet=True).all()
#     for prof in all_the_profile:
#         # prof.remit_inv_funds_to_wallet = False

#         data['First_Name'].append(f"{prof.first_name}")
#         data['Last_Name'].append(f"{prof.last_name}")
#         data['Email'].append(f"{prof.user.email}")
#         data['Phone_Number'].append(f"{prof.phone}")
#         # prof.save()

#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     #new_df.to_excel(f"cip_investment_roi_payouts_real_{set_date}.xlsx", index = False, header=True)
#     new_df.to_excel(f"users_with_pay_to_wallet.xlsx", index = False, header=True)

#     context = {
#             'the_data':data
#         }

#     return render(request, template, context)

    
# def get_all_false_ended_investment(request):
#     data_col = ['Email', 'Invested_Amount',  'Invested_Start', 'Invested_Ended',]
#     data = {
#             'Email':[], 'Invested_Amount':[], 'Invested_Start':[], 'Invested_Ended':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
#     today = datetime.date(datetime.astimezone(datetime.today()))
#     print(today)
#     cip_investments = UserInvestment.objects.filter(active=True, plan__category__name="CIP", completed=False).all()
#     for inv in cip_investments:
#         prof = inv.user
#         if inv.maturity_date.date() < today:
#             print(f"There is a problem with {inv.txn_code} user {prof.user.email}")
#             data['Email'].append(f"{prof.user.email}")
#             data['Invested_Amount'].append(f"{inv.amount}")
#             data['Invested_Start'].append(f"{inv.created_at.date()}")
#             data['Invested_Ended'].append(f"{inv.maturity_date}")
#             # prof.save()

#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     #new_df.to_excel(f"cip_investment_roi_payouts_real_{set_date}.xlsx", index = False, header=True)
#     new_df.to_excel(f"false_ended_invs.xlsx", index = False, header=True)

#     context = {
#             'the_data':data
#         }

#     return render(request, template, context)


# class CIP_ROLLOVER(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():
                
#                     plan_cat = InvestmentPlan.objects.get(percentage_interest=int(row['percentage(per/month)']))
#                     print(plan_cat)
                

#                     inv_started = str(row['investment started'])
#                     day, month, year = inv_started.split('/')
#                     investment_started = '/'.join((month, day, year))
#                     investment_started_date = datetime.strptime(investment_started, '%m/%d/%Y')
#                     print(investment_started_date)
                    
                   
                    

#                     inv_duration = int(row['investment duration'])
#                     investment_ends_date = investment_started_date + relativedelta(months=inv_duration)
#                     print(investment_ends_date)
                    
#                     the_email =  str(row['email']).lower().strip()
#                     print(the_email)  

                   
#                     get_user = User.objects.filter(email=the_email)

#                     if get_user.exists():
#                         the_user = get_user[0]
#                         print(the_user)
#                         print("Hurray, User exists")  

#                         if investment_ends_date < datetime.today():
#                             print("this investment has ended")
#                             print("this investment has ended")
#                             print("this investment has ended")
                            
 
#                         elif investment_ends_date > datetime.today():
                            
#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             if amount_inv < plan_cat.max_investment:


#                                 inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                                 new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = the_user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), cip_pioneer=True, active=True, mig_batch='six(rollover)', completed=False)


#                                 time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                                 print(time_dif.days)

#                                 new_user_investment.maturity_days = time_dif.days
#                                 new_user_investment.is_rollover = True
#                                 new_user_investment.save()


#                                 new_user_inv_earning = UserInvestmentEarnings.objects.create(user=the_user.profile,plan=new_user_investment, amount=0, active=True)
                                

#                                 p = lambda x: x/100
#                                 daily_percentage = (new_user_investment.plan.percentage_interest) / 30 
#                                 ur_daily_earning = float(new_user_investment.amount) *p(daily_percentage)
#                                 print(ur_daily_earning)

                                
                                
#                                 today = datetime.astimezone(datetime.today())
                                
#                                 start_date = new_user_investment.created_at
#                                 end_date = new_user_investment.maturity_date


#                                 the_range = pd.date_range(start=start_date, end=end_date,freq='30D').to_pydatetime().tolist()
#                                 print(the_range)
#                                 for i in the_range:
#                                     print(i.year)
#                                     if i.year == datetime.astimezone(datetime.now()).year:
                                    
#                                         if  i.month ==  datetime.astimezone(datetime.now()).month and today > i:
#                                             ur_last_payout = i 
                                            
#                                             ur_next_payout = i + timedelta(30)

                                            
                                            
#                                             print(f"You have been paid for this month on the {ur_last_payout}, the next payout is {ur_next_payout}")
#                                             new_user_investment.next_payout = ur_next_payout
                                            
#                                             nos_days = (datetime.date(today) - datetime.date(ur_last_payout)).days
#                                             print(nos_days)

#                                             new_user_investment.profit_earned = int(ur_daily_earning * nos_days)
#                                             new_user_investment.save()

#                                             new_user_inv_earning.amount = int(ur_daily_earning * nos_days)
#                                             new_user_inv_earning.save()
                                            

                                            


#                                         elif i.month ==  datetime.astimezone(datetime.now()).month and today < i:
                                            
                                            
#                                             ur_next_payout = i
#                                             ur_last_payout = i -  timedelta(30)

#                                             print(f"Gbam, the next payout is {ur_next_payout}")
#                                             print(f"Last month was {ur_last_payout} ")

#                                             new_user_investment.next_payout = ur_next_payout
                                            

                                        
                                            
#                                             nos_days = (datetime.date(today) - datetime.date(ur_last_payout)).days
#                                             print(nos_days)

#                                             new_user_investment.profit_earned = int(ur_daily_earning * nos_days)
#                                             new_user_investment.save()

#                                             new_user_inv_earning.amount = int(ur_daily_earning * nos_days)
#                                             new_user_inv_earning.save()
#                                     else:
#                                         print(f"no be this year o, na {i.year}")
#                                     print(i)
#                             else:
#                                 print(f"{amount_inv} is more than the max investment for this plan")
#                     else:
#                         print(f"{the_email} does not exist")


#                 print("All investements have been treated")

#                 return HttpResponseRedirect(reverse("users:process_rollover"))


    
#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:process_rollover"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:process_rollover"))






#Pending 

# class HIP_ROLLOVER(View):
#     def get(self, request, *args, **kwargs):
#         template = 'users/admin_user_import.html'
#         form = ImportUserForm()
#         context = {
#             'form':form
#         }

#         return render(self.request, template, context)
    
#     def post(self, request, *args, **kwargs):

#         form = ImportUserForm(self.request.POST, self.request.FILES or None)
#         User = get_user_model()
#         try:
#             if form.is_valid():

#                 document = form.cleaned_data.get('document')
#                 new_doc = UserImportDoc(doc=document)
#                 new_doc.save()

#                 the_doc = UserImportDoc.objects.filter(pk=new_doc.pk).first()
                


#                 the_import = pd.read_csv(the_doc.doc).fillna('')
#                 the_import.columns = the_import.columns.str.strip().str.lower()

#                 for index, row in the_import.iterrows():

#                     plan_cat = InvestmentPlan.objects.get(percentage_interest=int(row['percentage(per/month)']))
#                     print(plan_cat)
                

#                     inv_started = str(row['investment started'])
#                     day, month, year = inv_started.split('/')
#                     investment_started = '/'.join((month, day, year))
#                     investment_started_date = datetime.strptime(investment_started, '%m/%d/%Y')
#                     print(investment_started_date)
                    
                   
                    

#                     inv_duration = int(row['investment duration'])
#                     investment_ends_date = investment_started_date + relativedelta(months=inv_duration)
#                     print(investment_ends_date)
                    
#                     the_email =  str(row['email']).lower().strip()
#                     print(the_email)  

#                     # get_user = User.objects.filter(email=the_email)
#                     get_user = User.objects.filter(email=the_email)

#                     if get_user.exists():
#                         the_user = get_user[0]
#                         print(the_user)
#                         print("Hurray, User exists")  

                            
#                         if investment_ends_date > datetime.today():
                            
#                             amount_inv = int(row['amount(digits)'])
#                             print(amount_inv)

#                             inv_transaction_code = str(''.join(random.choices(string.digits, k = 13)))
#                             new_user_investment = UserInvestment.objects.create(txn_code=inv_transaction_code, user = the_user.profile,amount = amount_inv, plan=plan_cat, created_at=make_aware(investment_started_date), maturity_date = make_aware(investment_ends_date), hip_pioneer=True, active=True, mig_batch='one', completed=False)


#                             time_dif = datetime.date(new_user_investment.maturity_date) - datetime.date(new_user_investment.created_at)
#                             print(time_dif.days)

#                             new_user_investment.maturity_days = time_dif.days
#                             new_user_investment.next_payout = new_user_investment.maturity_date
#                             new_user_investment.save()


#                             new_user_inv_earning = UserInvestmentEarnings.objects.create(user=the_user.profile,plan=new_user_investment, amount=0, active=True)
                            

#                             p = lambda x: x/100
#                             daily_percentage = (new_user_investment.plan.percentage_interest) / int(new_user_investment.maturity_days)
#                             print(daily_percentage) 
#                             ur_daily_earning = float(new_user_investment.amount) *p(daily_percentage)
#                             print(ur_daily_earning)

                            
                             
#                             today = datetime.astimezone(datetime.today())
                            
#                             start_date = new_user_investment.created_at
#                             end_date = new_user_investment.maturity_date

#                             nos_days_earned = (datetime.date(today) - datetime.date(start_date)).days
#                             print(nos_days_earned)

#                             new_user_investment.profit_earned = int(ur_daily_earning * nos_days_earned)
#                             new_user_investment.save()


#                             new_user_inv_earning.amount = int(ur_daily_earning * nos_days_earned)
#                             new_user_inv_earning.save()
#                         else:
#                             print("Something went wrong, pls check !")

                    

#                 print("All users have been imported")
#                 return HttpResponseRedirect(reverse("users:hip-import"))



            
#             return HttpResponseRedirect(reverse("users:hip-import"))
                

#         except (ValueError, NameError, TypeError) as error:
#             err_msg = str(error)
#             print(err_msg)
#             return HttpResponseRedirect(reverse("users:hip-import"))
#         except:
#             print("Unexpected Error")
#             raise
#             return HttpResponseRedirect(reverse("users:hip-import"))



# def correct_celery_lag(request):
#     data_col = ['Investor_Name', 'Investor_Address', 'Investor_Email',  'Invested_Amount', 'Investment_Duration', 'Investment_Started_Date', 'Investment_Plan_Type']
#     data = {
#             'Investor_Name':[], 'Investor_Address':[], 'Investor_Email':[], 'Invested_Amount':[], 'Investment_Duration':[], 'Investment_Started_Date':[], 'Investment_Plan_Type':[]
#                         }
#     template = 'users/multiple_sponsor_check.html'
  
#     payout_date_str = '05/04/21 00:00:00'
#     payout_date = datetime.strptime(payout_date_str, '%d/%m/%y %H:%M:%S').date()

#     cip_investments = UserInvestment.objects.filter(plan__category__name="CIP", cip_pioneer=False, active=True, completed=False).all()
#     for inv in cip_investments:
#         user_profile = inv.user
#         if inv.maturity_date.date() == payout_date:
#             print("Data is here!")
#             print(f"Investment amount is {inv.amount}")

        
#             data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#             data['Investor_Address'].append(f"{user_profile.address_1} - {user_profile.address_2} - {user_profile.city} - {user_profile.state} - {user_profile.nationality}")
#             data['Investor_Email'].append(f"{user_profile.user.email}")
#             data['Invested_Amount'].append(inv.amount)
#             data['Investment_Duration'].append(f"{int(int(inv.maturity_days)/30)}")
#             data['Investment_Started_Date'].append(f"{inv.created_at.date()}")
#             data['Investment_Plan_Type'].append(f"{inv.plan.category.name}")



#             # user_earnings = UserInvestmentEarnings.objects.filter(user=user_profile,plan=inv).first()


            


#             # p = lambda x: x/100
#             # amount = inv.amount
#             # plan = inv.plan
#             # percentage = plan.percentage_interest
#             # maturity_date = inv.maturity_date
#             # created_date = inv.created_at
#             # next_payout = inv.next_payout
#             # daily_percentage = int(percentage) / 30 
#             # earning = float(amount) *p(daily_percentage)




#             # transaction_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)))

#             # payout_this_month = user_earnings.amount

#             # new_payment = Payments.objects.create(txn_code=transaction_code, amount=payout_this_month, user = user_earnings.user, destination="bank_account", status='pending',remark=f"CIP ROI Payout for {user_earnings.plan.txn_code} - {user_earnings.plan.display_name}")

#             # new_roi_tnx = Transaction.objects.create(amount=user_earnings.amount, txn_code=transaction_code, user = user_earnings.user, txn_method="manual", txn_type='investment_earnings')

#             # user_earnings.plan.profit_earned += earning
#             # user_earnings.plan.profit_paid += payout_this_month

            

#             # user_earnings.amount = earning
#             # user_earnings.save()
#             # user_earnings.plan.next_payout  += timedelta(30)
#             # user_earnings.plan.save()


#             # print(f"done with {user_profile.user.email} ")


            

                
           
            
#         # else:
#         #     print("Investment record not in time frame")
          
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
#     # new_df.to_csv(f"investment_records_for_sponsors_4.csv", index = False, header=True)
#     #new_df.to_excel(f"all_investments_{start_date}_to_{end_date}.xlsx")
#     # new_df.to_excel(f"all_the_missed_payout.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)




# def correct_celery_lag_daily(request):
#     data_col = ['Investor_Name', 'Investor_Email' , 'Invested_Amount', 'Investment_Earning_Now', 'Investment_Earning_ShouldBE']
#     data = {
#             'Investor_Name':[], 'Investor_Email':[] ,'Invested_Amount':[], 'Investment_Earning_Now':[], 'Investment_Earning_ShouldBE':[], 
#                         }

#     today = datetime.date(datetime.astimezone(datetime.today()))
#     print(today)
#     template = 'users/multiple_sponsor_check.html'
  
#     payout_date_str = '05/04/21 00:00:00'
#     payout_date = datetime.strptime(payout_date_str, '%d/%m/%y %H:%M:%S').date()

#     cip_investments = UserInvestment.objects.filter(plan__category__name="CIP", cip_pioneer=False, active=True, completed=False).all()
#     for inv in cip_investments:
#         user_profile = inv.user
        
#         if not inv.user_investment_topup.exists():
#             pass
#             # print("Data is here!")
#             # print(f"Investment amount is {inv.amount}")

        
            
           
           

#             # user_earning = UserInvestmentEarnings.objects.filter(user=user_profile,plan=inv).first()

#             # print(f"current earning is reading {user_earning.amount}")
            




#             # p = lambda x: x/100
#             # amount = inv.amount
#             # plan = inv.plan
#             # percentage = plan.percentage_interest
#             # maturity_date = inv.maturity_date
#             # created_date = inv.created_at
#             # next_payout = inv.next_payout
#             # daily_percentage = int(percentage) / 30 
#             # earning = float(amount) *p(daily_percentage)
#             # print(f"earning power is {earning} ")

#             # print(f"last payout was {inv.get_last_payout}")


#             # day_diff = (today - inv.get_last_payout).days
#             # print(f"day difference is {day_diff} ")

#             # real_roi_today = int(earning * day_diff)
#             # print(f" real roi calculated is {real_roi_today}")

#             # if day_diff <= 30:

                

#             #     if int(real_roi_today) != int(user_earning.amount):

#             #         print(f"there is a prob, roi today should be {real_roi_today}")
#             #         data['Investment_Earning_ShouldBE'].append(f"{real_roi_today}")
#             #         data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#             #         data['Investor_Email'].append(f"{user_profile.user.email}")
#             #         data['Invested_Amount'].append(inv.amount)
#             #         data['Investment_Earning_Now'].append(user_earning.amount)

#             #         # user_earning.amount = int(real_roi_today)
#             #         # user_earning.save()
#             #         # inv.profit_earned += int(earning)
#             #         # inv.save()


                
#             # else:
#             #     print(f"user{inv.user} payout was affected")
#         else:
#             last_topup =  inv.user_investment_topup.last() 
#             print(f"New Capital is {inv.amount}")   
#             print(f"old capital is {(inv.amount - last_topup.amount)}")
            

#             user_earning = UserInvestmentEarnings.objects.filter(user=user_profile,plan=inv).first()
#             print(f"current user is {inv.user.user.email}")
#             print(f"current earning is reading {user_earning.amount}")


#             p = lambda x: x/100
#             new_amount = inv.amount
#             old_amount = inv.amount - last_topup.amount
#             plan = inv.plan
#             percentage = plan.percentage_interest
#             maturity_date = inv.maturity_date
#             created_date = inv.created_at
#             next_payout = inv.next_payout
#             daily_percentage = int(percentage) / 30 
#             old_earning = float(old_amount) *p(daily_percentage)
#             new_earning = float(new_amount) *p(daily_percentage)
#             print(f"earning power was {old_earning}")
#             print(f"earning power is {new_earning}")

#             nos_days_b4tp = (last_topup.created_at.date() - inv.get_last_payout).days
#             print(f"no of days b4 topup is {nos_days_b4tp}")

#             roi_b4tp = int(nos_days_b4tp * old_earning)
#             print(f"roi before topup {roi_b4tp}")

#             nos_days_aftertp = (today - last_topup.created_at.date()).days
#             print(f"no of days after topup is {nos_days_aftertp} ")

#             roi_aftertp = int(nos_days_aftertp * new_earning)
#             print(f"roi after topup is {roi_aftertp} ")

#             total_roi = roi_b4tp + roi_aftertp
#             print(f"the total roi {total_roi}")

#             day_diff = (today - inv.get_last_payout).days

#             if day_diff <= 30:

#                 if int(total_roi) != int(user_earning.amount):
#                     print(f"there is a prob, roi today should be {total_roi}")
#                     print(f"investment started in {inv.created_at.date()}")
#                     data['Investment_Earning_ShouldBE'].append(f"{total_roi}")
#                     data['Investor_Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
#                     data['Investor_Email'].append(f"{user_profile.user.email}")
#                     data['Invested_Amount'].append(inv.amount)
#                     data['Investment_Earning_Now'].append(user_earning.amount)

#                     user_earning.amount += int(new_earning)
#                     user_earning.save()

#                     inv.profit_earned += int(new_earning)
#                     inv.save()






   
#     print(data)
#     new_df = pd.DataFrame({key:pd.Series(value) for key, value in data.items() }, columns=data_col)
#     new_df = new_df.drop_duplicates(keep = False, inplace = False)
    
#     new_df.to_excel(f"all_the_missed_rois_with_topup.xlsx")

#     context = {
#             'the_data':data
#         }
   
  
#     return render(request, template, context)



# def get_all_pioneers(request):
#     all_prof = Profile.objects.all()
#     for prof in all_prof:
#         if prof.pioneer_ppp_reg_expires != None:
#             print(f"possible partner, expires {prof.pioneer_ppp_reg_expires}")

#             prof.pioneer_ppp_reg_expires += timedelta(days=365)
#             prof.pioneer_ppp_member = True
#             prof.save()
#             print(f"reg expires now {prof.pioneer_ppp_reg_expires}")
#         else:
#             print(f"not a pioneer")
            
#     return redirect('/')