import csv
from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from users.models import *

class Command(BaseCommand):
    help = 'Load users from csv file into the database'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str)

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        User = get_user_model()
        with open(path, 'rt') as f:
            reader = csv.reader(f, dialect='excel')
            for row in reader:
                # print(str(row[0].split("@", 1)[0]))
               
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
                    basic_membership = Membership.objects.get(membership_type='free')
                    user_membership.paystack_customer_id = new_customer['data']['id']
                    user_membership.paystack_unique_user_id = new_customer['data']['customer_code']
                    user_membership.membership = basic_membership
                    user_membership.save()

                # user_profile = user.profile
                # user_profile. 



                user_bank_account, created = UserBankAccount.objects.get_or_create(user=user.profile)
                next_of_kin, created = NextOfKin.objects.get_or_create(user=user.profile)
                user_document, created = UserDocument.objects.get_or_create(user=user.profile)
                user_wallet, created = MainWallet.objects.get_or_create(user=user.profile)
                user_investment_wallet, created = InvestmentWallet.objects.get_or_create(user=user.profile)
                user_referral_wallet, created = ReferralWallet.objects.get_or_create(user=user.profile)




        self.stdout.write(self.style.SUCCESS(
            'All users have been imported' ))