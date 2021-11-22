from rest_framework import serializers
from users.models import *
from django.contrib.auth.models import User
from datetime import datetime
from django.utils.timesince import timesince



class UserSubscriptionSerializer(serializers.ModelSerializer):
    next_billing_date = serializers.SerializerMethodField()
    class Meta:
        model = Subscription
        exclude = ("id",)

    def get_next_billing_date(self,object):
        user_next_billing_date = object.get_next_billing_date
        if user_next_billing_date:
            return user_next_billing_date
        return None

class UserMembershipSerializer(serializers.ModelSerializer):
    user_subscription = UserSubscriptionSerializer(many=True, read_only=True)
    class Meta:
        model = UserMembership
        exclude = ("id",)

class UserSerializer(serializers.ModelSerializer):

    usermembership = UserMembershipSerializer(read_only=True)

    class Meta:
        model = User
        exclude = ("id",)

class UserDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDocument
        exclude = ("id",)

class UserBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBankAccount
        exclude = ("id",)

class UserNextOfKinSerializer(serializers.ModelSerializer):
    class Meta:
        model = NextOfKin
        exclude = ("id",)



class ProfileSerializer(serializers.ModelSerializer):

    has_active_investment = serializers.SerializerMethodField()
    active_investment_sum = serializers.SerializerMethodField()
    time_joined = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
   
    user = UserSerializer(read_only=True)
    user_documents = UserDocumentsSerializer(many=True, read_only=True) 
    user_bank_account = UserBankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        exclude = ("id",)
        
    def get_has_active_investment(self, object):
        user_has_active_investment = object.has_active_investment
        return user_has_active_investment

    def get_active_investment_sum(self,object):
        user_active_investment_sum = object.has_active_investment_sum
        return user_active_investment_sum

    def get_time_joined(self, object):
        created_at = object.created_at
        time_delta = created_at.strftime('%Y-%m-%d %H:%M')
        return time_delta

    def get_last_login(self,object):
        the_last_login = object.last_login
        return the_last_login

 

class ReferralsSerializer(serializers.ModelSerializer):
    sponsor = ProfileSerializer(read_only=True)
    downline = ProfileSerializer(read_only=True)
    class Meta:
        model = UserReferrals
        fields = '__all__'

   
    

    








