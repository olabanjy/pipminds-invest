from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.template.loader import render_to_string
from .models import *
from .utils import *
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
def start_running_pool(): 
    today = datetime.astimezone(datetime.today())
    #check all pending pools
    pending_pools = PoolInstance.objects.filter(status="pending").all()
    for pool in pending_pools:
        # check of today is greater than entry ends 
        if datetime.date(today) >= pool.entry_ends:
            #activate pool and change pool status to running
            pool.status = "running"
            pool.active = True
            #assign a run start day 
            pool.run_starts = pool.entry_ends  + timedelta(1)
            pool.save()
            #check pool active period window
            pool_run_period = pool.pool_type.active_period_window.period_days
            #assign a run ends day
            pool.run_ends = pool.run_starts + timedelta(int(pool_run_period))
            pool.save()

            print(f"Finished level 1")
            #SEND AGREEMENT TO ALL USER POOLS 

            user_pools = UserPoolSlots.objects.filter(pool_instance=pool).all()
            for user_pool in user_pools:
                contract_data = {
                        'first_name': user_pool.user.first_name,
                        'last_name': user_pool.user.last_name,
                        'slots_taken': int(user_pool.slots_taken),
                        'slots_value': int(user_pool.slots_value)                  
                        }
                
                contract_filename = f"PREMIUM_POOL_AGREEMENT_{user_pool.tnx_code}.pdf"

                new_render_to_file_pools('contracts/premium_pool_contract.html',contract_filename, user_pool.pk, contract_data)

                try:
                    contract_file = user_pool.contract_file
                    response = requests.get(contract_file.url)
                    subject, from_email, to = 'Pool Investment is now Active', 'PIPMINDS <hello@pipminds.com>', [
                                user_pool.user.user.email]

                    html_content = render_to_string(
                        'events/pool_running.html', {
                            'first_name': user_pool.user.first_name,
                            'last_name':user_pool.user.last_name,    
                        })
                    msg = EmailMessage(subject, html_content, from_email, to)
                    msg.content_subtype = "html"
                    msg.attach(contract_filename, response.content, mimetype="application/pdf")
                    msg.send()
                    print("contract sent out ")


                except (ValueError, NameError, TypeError) as error:
                    err_msg = str(error)
                    print(err_msg)
                    
                except:
                    print("Unexpected Error")
            print("finished Level 2")
            #Create a new pool instance 
            unq_code = str(''.join(random.choices(string.ascii_uppercase + string.digits, k = 8)))
            new_pool_instance = PoolInstance.objects.create(unique_instance_id=f"PPI-{unq_code}", pool_type=pool.pool_type, status="pending", entry_starts=datetime.date(today), approved=True)
            #check pool entry period window
            pool_entry_period = pool.pool_type.entry_window.period_days
            #assign new pool entry ends 
            new_pool_instance.entry_ends = new_pool_instance.entry_starts + timedelta(int(pool_entry_period))
            new_pool_instance.save()

            print("finished Level 3")


@shared_task
def end_completed_pools():
    today = datetime.astimezone(datetime.today())
    #check all pending pools
    running_pools = PoolInstance.objects.filter(status="running").all()
    for pool in running_pools:
    # check of today is greater than entry ends 
        if datetime.date(today) >= pool.run_ends:
            pool.status = "completed"
            pool.active = False
            pool.save()
            print("Pool ended!")









