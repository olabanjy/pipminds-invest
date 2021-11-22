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
import requests


flutterwave_secret_key = settings.TEST_FLUTTERWAVE_SECRET_KEY





class ExplorePools(View):
    def get(self, request, *args, **kwargs):

        user_wallet, created = PoolsWallet.objects.get_or_create(user=self.request.user.profile)
        pools  = PoolInstance.objects.filter(approved=True, status="pending").all()
        already_active_pools = PoolInstance.objects.filter(approved=True,active=True, status="running").all()
        pool_offerings = PoolOfferings.objects.all()
        check_offering_purchase = UserOfferingsPurchase.objects.filter(user=self.request.user.profile)
        wallet_balance = user_wallet.deposit
        template = "pools/explore.html"
        context = {
            'pools': pools,
            'already_active_pools': already_active_pools,
            'wallet_balance': wallet_balance,
            'pool_offerings': pool_offerings,
            'check_offering_purchase':check_offering_purchase
        }

        return render(self.request, template, context)

    def post(self, request, *args, **kwargs):
        
        pool_instance_id = self.request.POST.get('chosen_pool_unique_id', None)
        chosen_slot_number = self.request.POST.get('chosen_slot_number', None)
        offerings = self.request.POST.getlist('chosen_offering', None)
        print(pool_instance_id)
        print(offerings)

        the_slot_nos = None
        
        if chosen_slot_number == "" or None:
            the_slot_nos = 1
        else:
            the_slot_nos = chosen_slot_number

        print(the_slot_nos)

        get_pool = PoolInstance.objects.get(unique_instance_id=pool_instance_id)
        print(get_pool)

        user_wallet, created = PoolsWallet.objects.get_or_create(user=self.request.user.profile)


        if offerings == None:

            total_cost = 0

            total_cost += int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
            print(f"total cost to be spent is {total_cost}")
            print(f"user deposit wallet is  {int(user_wallet.deposit)}")


            if int(user_wallet.deposit) <= total_cost:
                print("There is not enough funds to proceed")
                messages.error(self.request, "There is not enough funds to proceed!")
                return HttpResponseRedirect(reverse('pools:explore'))

            get_user_pool_slots = UserPoolSlots.objects.filter(user=self.request.user.profile, pool_instance=get_pool)
            if get_user_pool_slots.exists():
                print("user slot already exist")
                #Deduct value from wallet
                user_wallet.deposit -= int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                user_wallet.save()
                #Update user pool slots
                the_user_slots = get_user_pool_slots.first()
                the_user_slots.slots_taken += int(the_slot_nos)
                the_user_slots.slots_value += get_pool.pool_type.amount_per_slot * int(the_slot_nos)
                the_user_slots.save()

                # update pool instance
                get_pool.slots += int(the_slot_nos)
                get_pool.value_bought += int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                get_pool.save()
            
            else:
                print("user slots does not exist before")

                #Deduct value from wallet
                user_wallet.deposit -= int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                user_wallet.save()

                # create new user pool slot
                transaction_code =f"PP{str(''.join(random.choices(string.ascii_uppercase  + string.digits, k = 16)))}"
                new_user_slots = UserPoolSlots.objects.create(tnx_code=transaction_code, user=self.request.user.profile, pool_instance=get_pool,slots_taken=int(the_slot_nos))
                new_user_slots.slots_value = get_pool.pool_type.amount_per_slot * new_user_slots.slots_taken
                new_user_slots.save()

                # update pool instance
                get_pool.slots += int(the_slot_nos)
                get_pool.value_bought += int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                get_pool.save()
            return HttpResponseRedirect(reverse('pools:explore'))

        elif offerings != None:
            print(offerings)

            total_cost = 0

            for offering_name in offerings:
                offer = PoolOfferings.objects.get(name=offering_name)
                total_cost += int(float(offer.price))
            
            total_cost += int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))

            print(f"total cost to be spent is {total_cost}")
            print(f"user deposit wallet is  {int(user_wallet.deposit)}")

            if int(user_wallet.deposit) <= total_cost:
                print("There is not enough funds to proceed")
                messages.error(self.request, "There is not enough funds to proceed!")
                return HttpResponseRedirect(reverse('pools:explore'))


            user_offering_purchase, created = UserOfferingsPurchase.objects.get_or_create(user=self.request.user.profile)

            for offer_name in offerings:
                offer = PoolOfferings.objects.get(name=offer_name)
                user_offering_purchase.offerings.add(offer)
                user_offering_purchase.total_amount += int(float(offer.price))
                user_offering_purchase.save()
            
            #first wallet deduction (1) Deduct offering value from wallet 
            user_wallet.deposit -= int(user_offering_purchase.total_amount)
            user_wallet.save()



            get_user_pool_slots = UserPoolSlots.objects.filter(user=self.request.user.profile, pool_instance=get_pool)
            if get_user_pool_slots.exists():
                print("user slot already exist")
                #Second deduction (2) Deduct value from wallet
                user_wallet.deposit -= int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                user_wallet.save()

                # update user pool slots
                the_user_slots = get_user_pool_slots.first()
                the_user_slots.slots_taken += int(the_slot_nos)
                the_user_slots.slots_value += get_pool.pool_type.amount_per_slot * int(the_slot_nos)
                the_user_slots.save()

                # update pool instance
                get_pool.slots += int(the_slot_nos)
                get_pool.value_bought += int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                get_pool.save()
            
            else:
                print("user slots does not exist before")

                #Deduct value from wallet
                user_wallet.deposit -= int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                user_wallet.save()

                # create a new user pool slot
                transaction_code =f"PP{str(''.join(random.choices(string.ascii_uppercase  + string.digits, k = 16)))}"
                new_user_slots = UserPoolSlots.objects.create(tnx_code=transaction_code, user=self.request.user.profile, pool_instance=get_pool,slots_taken=int(the_slot_nos))
                new_user_slots.slots_value = get_pool.pool_type.amount_per_slot * new_user_slots.slots_taken
                new_user_slots.save()

                # update pool instance
                get_pool.slots += int(the_slot_nos)
                get_pool.value_bought += int(get_pool.pool_type.amount_per_slot * int(the_slot_nos))
                get_pool.save()

            return HttpResponseRedirect(reverse('pools:explore'))





        
class PoolsWalletsView(View):
    def get(self, request, *args, **kwargs):

        if not self.request.user.profile.profile_set_up:
            return redirect('users:profile-set-up')

        if not self.request.user.profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
      
        
        pools_wallet = None
        user_pool_wallet = PoolsWallet.objects.filter(user=self.request.user.profile)
        
        if user_pool_wallet.exists():
            pools_wallet = user_pool_wallet.first()
        
        template = 'pools/wallet.html'
        context = {
            'pools_wallet': pools_wallet
            
        }

        return render(self.request, template, context) 

    def post(self, request, *args, **kwargs):
        tranx_id = request.POST['flutterTranxID']
        tranx_ref = request.POST['flutterTranxRef']
        print(tranx_id)
        print(tranx_ref)
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

                user_pools_wallet, created = PoolsWallet.objects.get_or_create(user=self.request.user.profile)
                user_pools_wallet.deposit += response['data']['amount']
                user_pools_wallet.save()

               
                

                print("The card was charged")
                messages.error(self.request, "Your card was charged !")
                return redirect(reverse('pools:wallet'))
            else:
                messages.error(self.request, 'Payment failed')
                return HttpResponseRedirect(reverse('pools:wallet'))
                
        except (ValueError, NameError, TypeError) as error:
            err_msg = str(error)
            print(err_msg)
        except:
            print("Unexpected Error")
            raise



class MyPoolInvestments(View):
    def get(self, request, *args, **kwargs):

        pending_user_slots = UserPoolSlots.objects.filter(pool_instance__status="pending", user=self.request.user.profile).all()
        active_user_slots = UserPoolSlots.objects.filter(pool_instance__status="running", user=self.request.user.profile).all()
        completed_user_slots = UserPoolSlots.objects.filter(pool_instance__status="completed", user=self.request.user.profile).all()

        template = 'pools/mypools.html'
        context ={
            'pending_user_slots':pending_user_slots,
            'active_user_slots': active_user_slots,
            'completed_user_slots': completed_user_slots
        }

        return render(self.request, template, context)















            



