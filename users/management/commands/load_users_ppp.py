import csv
from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from users.models import *
import time

class Command(BaseCommand):
    help = 'Load users from csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        User = get_user_model()
        with open(path, 'r', encoding='Latin1') as f:
            reader = csv.reader(f, dialect='excel')
            for row in reader:
                # print(str(row[0].split("@", 1)[0]))
                # time.sleep(20)
               
                user, created = User.objects.get_or_create(
                    username=str(row[0].split("@", 1)[0]),

                defaults={
                    'email':str(row[0]),
                    'password': make_password('ddff123#')
                }
                )
                
                user_membership, created = UserMembership.objects.get_or_create(user=user)
                if user_membership.paystack_customer_id is None or user_membership.paystack_customer_id == '':
                    new_customer = paystack.customer.create(email=user.email)
                    print(new_customer['status'])
                    basic_membership = Membership.objects.get(membership_type='free')
                    user_membership.paystack_customer_id = new_customer['data']['id']
                    user_membership.paystack_unique_user_id = new_customer['data']['customer_code']
                    user_membership.membership = basic_membership
                    user_membership.save()

                user_profile = user.profile

                user_profile.phone = str(row[9])
                user_profile.first_name = str(row[3])
                user_profile.last_name = f"{str(row[1])} {str(row[2])}"
                the_pioneer_ppp_reg_expires = str(row[5])
                month, day, year = the_pioneer_ppp_reg_expires.split('/')
                user_profile.pioneer_ppp_reg_expires = '-'.join((year, month, day))
                user_profile.address_1 = str(row[7])
                user_profile.state = str(row[6])
                user_profile.nationality = str(row[8])
                user_profile.profile_set_up = True
                user_profile.investment_kyc_submitted = True
                user_profile.investement_verified = "approved"
                user_profile.ppp_started = True
                user_profile.ppp_verfied = True 
                user_profile.save()


                user_bank_account, created = UserBankAccount.objects.get_or_create(user=user.profile)
                next_of_kin, created = NextOfKin.objects.get_or_create(user=user.profile)
                user_document, created = UserDocument.objects.get_or_create(user=user.profile)
                user_wallet, created = MainWallet.objects.get_or_create(user=user.profile)
                user_investment_wallet, created = InvestmentWallet.objects.get_or_create(user=user.profile)
                user_referral_wallet, created = ReferralWallet.objects.get_or_create(user=user.profile)

                user_bank_account.bank_name = str(row[10])
                user_bank_account.account_name = str(row[11])
                user_bank_account.account_number = str(row[12])
                user_bank_account.save()

                print(f"done with {str(row[0])}")




        self.stdout.write(self.style.SUCCESS(
            'All users have been imported' ))