from rest_framework import status
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import JsonResponse
from users.models import * 
from users.api.serializers import * 
from users.api.pagination import MyDefaultSetPagination
from users.tasks import send_kyc_verified_email,send_kyc_rejected_email
from datetime import timedelta, date, datetime, time
from investment.models import UserInvestment,UserInvestmentEarnings


# class ProfileSerializerListCreateAPIView(APIView):
#     def get(self, request):
#         profiles = Profile.objects.all()
#         serializer = ProfileSerializer(profiles, many=True)
#         return Response(serializer.data)   

class ProfileSerializerListCreateAPIView(generics.ListAPIView):
    queryset = Profile.objects.all().order_by("-id")
    serializer_class = ProfileSerializer
    pagination_class = MyDefaultSetPagination


class UserSerializerListCreateAPIView(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)     
         

class ProfileDetailAPIView(APIView):

    def get_object(self, user_code):
        profile = get_object_or_404(Profile, user_code=user_code)
        return profile

    def get(self, request, user_code):
        profile = self.get_object(user_code)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)


    def patch(self, request, user_code):
        profile = self.get_object(user_code)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if 'investement_verified' in request.data:
                if request.data['investement_verified'] == "approved":
                    send_kyc_verified_email.delay(profile.user.pk)
                elif request.data['investement_verified'] == "rejected":

                    user_bank_account = UserBankAccount.objects.filter(user=profile).first()
                    user_bank_account.bank_name = None
                    user_bank_account.account_name = None
                    user_bank_account.account_number = None
                    user_bank_account.save()
                    
                    user_documents = UserDocument.objects.filter(user=profile).first()
                    user_documents.doc_front = None
                    user_documents.doc_back = None
                    user_documents.save()

                    user_next_of_kin = NextOfKin.objects.filter(user=profile).first()
                    user_next_of_kin.full_name
                    user_next_of_kin.email
                    user_next_of_kin.phone
                    user_next_of_kin.save()
                                            
                    send_kyc_rejected_email.delay(profile.user.pk)

                
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingKYCView(APIView):
    def get(self, request):
        profiles = Profile.objects.filter(investment_kyc_submitted=True,investement_verified="pending").all()
        serializer = ProfileSerializer(profiles, many=True)
        return Response(serializer.data)

class PartnersView(APIView):
    def get(self, request):
        profiles = Profile.objects.filter(ppp_verfied=True).all()
        serializer = ProfileSerializer(profiles, many=True)
        return Response(serializer.data)


class ReferralsView(generics.ListAPIView):
    queryset = UserReferrals.objects.all().order_by("-id")
    serializer_class = ReferralsSerializer
    pagination_class = MyDefaultSetPagination

class UniqueReferralsView(APIView):
    def get(self, request, user_code):
        downlines = UserReferrals.objects.filter(sponsor__user_code=user_code).all() 
        serializer =  ReferralsSerializer(downlines, many=True)
        return Response(serializer.data)



class UserBankAccountDetailAPIView(APIView):

    def get_object(self, user_code):
        account = get_object_or_404(UserBankAccount, user__user_code=user_code)
        return account

    def get(self, request, user_code):
        account = self.get_object(user_code)
        serializer = UserBankAccountSerializer(account)
        return Response(serializer.data)

    def patch(self, request, user_code):
        account = self.get_object(user_code)
        serializer = UserBankAccountSerializer(account, data=request.data, partial=True)
        if serializer.is_valid():
            if 'account_number' in request.data:
                acct_number = UserBankAccount.objects.filter(account_number=request.data['account_number'])
                if acct_number.exists():
                    raise ValidationError("Account Number Already exists !")
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserNextOfKinDetailAPIView(APIView):

    def get_object(self, user_code):
        next_of_kin = get_object_or_404(NextOfKin, user__user_code=user_code)
        return next_of_kin

    def get(self, request, user_code):
        next_of_kin = self.get_object(user_code)
        serializer = UserNextOfKinSerializer(next_of_kin)
        return Response(serializer.data)

    def patch(self, request, user_code):
        next_of_kin = self.get_object(user_code)
        serializer = UserNextOfKinSerializer(next_of_kin, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class GeneralUserSearchHandlerView(APIView):
    def get(self, request, user_email):
        profile = Profile.objects.get(user__email=user_email)
        print(profile)
        serializer =  ProfileSerializer(profile)
        return Response(serializer.data)



def cip_report(request, the_date):
    data = {
            'Email':[], 'Name':[], 'Invested_Amount':[], 'ROI':[], 'Account_Number':[], 'Bank':[], 'Payment_Preference':[]
                        }
    today = datetime.date(datetime.astimezone(datetime.today()))
    set_date_str = f"{the_date} 00:00:00"
    print(set_date_str)
    set_date = datetime.strptime(set_date_str, '%Y-%m-%d %H:%M:%S').date()
    print(set_date)
   
    cip_investments = UserInvestment.objects.filter(active=True, completed=False, cip_pioneer=False,hip_pioneer=False).all()
    for inv in cip_investments:
        
        if inv.next_payout:
            user_profile = inv.user     
            if  inv.next_payout.date() == set_date:
                print("Yes")
                user_account = UserBankAccount.objects.filter(user=user_profile).first()
                user_earning = UserInvestmentEarnings.objects.filter(user=user_profile,plan=inv).first()
                print(f"Data is here for user {inv.user.user.email}")
                print(f"Investment amount is {inv.amount}")


                print(f"Investment Earning now is {user_earning.amount}")

                print(f"Investment Profit Earned is {inv.profit_earned}")



                
                p = lambda x: x/100
                daily_percentage = (inv.plan.percentage_interest) / 30 
                print(daily_percentage) 
                ur_daily_earning = float(inv.amount) *p(daily_percentage)
                print(ur_daily_earning)

                nos_days_earned = (set_date  -  today).days
                print(nos_days_earned)

                extra_profit = int(ur_daily_earning * nos_days_earned)
                print(f"extra profit is {extra_profit}")

                total_roi = user_earning.amount + extra_profit
                print(f"total ROI is {total_roi}")
                
                data['Email'].append(f"{user_profile.user.email}")
                data['Name'].append(f"{user_profile.first_name} {user_profile.last_name}")
                data['Invested_Amount'].append(f"{inv.amount}")
                data['ROI'].append(f"{total_roi}")
                data['Account_Number'].append(user_account.account_number)
                data['Bank'].append(user_account.bank_name)
                if user_profile.remit_inv_funds_to_wallet == True:
                    data['Payment_Preference'].append('Pay To Wallet')
                else:
                    data['Payment_Preference'].append('Pay To Bank Account')
            else:
                pass
               
        else:
            print(f"error with {user_profile.user.email} payout date")
            print(f"error with {inv.txn_code}")
     
    print(data)
    response = JsonResponse(data)
    return response
