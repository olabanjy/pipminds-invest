from rest_framework import serializers
from investment.models import *
from users.api.serializers import ProfileSerializer
from datetime import datetime
from django.utils.timesince import timesince

class InvestmentPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentPeriod
        exclude = ("id",)


class InvestmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentCategory
        exclude = ("id",)

class InvestmentPlanSerializer(serializers.ModelSerializer):
    category = InvestmentCategorySerializer(read_only=True)
    period = InvestmentPeriodSerializer(read_only=True)
    class Meta:
        model = InvestmentPlan
        fields = '__all__'


class UserInvestmentSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True)
    plan = InvestmentPlanSerializer(read_only=True)
    next_payout = serializers.SerializerMethodField()
    started = serializers.SerializerMethodField()
    maturity_date = serializers.SerializerMethodField()

    class Meta:
        model = UserInvestment
        exclude = ("id",)

    def get_next_payout(self,object):
        next_payout = object.next_payout
        if next_payout:
            time_delta = next_payout.strftime('%Y-%m-%d %H:%M')
            return time_delta
    
    def get_started(self,object):
        started = object.created_at
        time_delta = started.strftime('%Y-%m-%d %H:%M')
        return time_delta
    
    def get_maturity_date(self,object):
        maturity_date = object.maturity_date
        time_delta = maturity_date.strftime('%Y-%m-%d %H:%M')
        return time_delta

class UserInvestmentEarningsSerializer(serializers.ModelSerializer):
    plan = UserInvestmentSerializer(read_only=True)
    class Meta:
        model = UserInvestmentEarnings
        exclude = ("id",)

    



