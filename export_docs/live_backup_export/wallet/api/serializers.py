from rest_framework import serializers
from users.api.serializers import ProfileSerializer
from django.contrib.auth.models import User
from datetime import datetime
from django.utils.timesince import timesince
from wallet.models import * 



class MainWalletSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True) 
    class Meta:
        model = MainWallet
        fields = '__all__'


class InvestmentWalletSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True) 
    class Meta:
        model = InvestmentWallet
        fields = '__all__'

class ReferralWalletSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True) 
    class Meta:
        model = ReferralWallet
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True) 
    class Meta:
        model = Transaction
        exclude = ("id",)

class DepositSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True) 
    created = serializers.SerializerMethodField()
    the_transaction_method = serializers.SerializerMethodField()
    class Meta:
        model = Deposit
        exclude = ("id",)
    
    def get_created(self, object):
        created_at = object.created_at
        time_delta = created_at.strftime('%Y-%m-%d %H:%M')
        return time_delta

    def get_the_transaction_method(self,object):
        the_trans = Transaction.objects.filter(txn_code=object.txn_code)
        if the_trans.exists():
            the_transaction = the_trans.first()
            the_method = the_transaction.txn_method
            return the_method
        return None

class WithdrawalSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True) 
    created = serializers.SerializerMethodField()
    
    class Meta:
        model = Withdrawal
        exclude = ("id",)

    def get_created(self, object):
        created_at = object.created_at
        time_delta = created_at.strftime('%Y-%m-%d %H:%M')
        return time_delta

class PaymentSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True)
    created = serializers.SerializerMethodField()

    class Meta:
        model = Payments
        fields = '__all__'

    def get_created(self, object):
        created_at = object.created_at
        time_delta = created_at.date()
        return time_delta




