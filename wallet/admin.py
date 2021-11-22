from django.contrib import admin
from .models import *



class UserWalletAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

class TransactionAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )
    list_display = ['user','txn_method', 'txn_type', 'amount', 'created_at', 'trans_ref']

class DepositAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )
    list_display = ['user','txn_code', 'status', 'approved', 'amount', 'created_at', 'trans_ref']

class WithdrawalAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )
    list_display = ['user','txn_code', 'status', 'approved', 'amount', 'created_at', 'trans_ref']

class PaymentAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )
    list_display = ['user', 'txn_code', 'status', 'approved', 'amount', 'created_at', 'destination', 'modified_at', 'remark']

class InvestmentWalletAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

class ReferralWalletAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

class UserReferralEarningWalletAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )


admin.site.register(MainWallet,UserWalletAdmin)
admin.site.register(InvestmentWallet, InvestmentWalletAdmin)
admin.site.register(ReferralWallet, ReferralWalletAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Withdrawal, WithdrawalAdmin)
admin.site.register(WebhookBackup)
admin.site.register(UserReferralEarnings, UserReferralEarningWalletAdmin)
admin.site.register(Deposit, DepositAdmin)
admin.site.register(Payments, PaymentAdmin)