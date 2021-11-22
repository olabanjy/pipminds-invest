from django import template
from wallet.models import *
from decimal import Decimal

register = template.Library()


@register.filter
def overall_balance(user):
    if user.is_authenticated:
        main_wallet = MainWallet.objects.filter(user=user.profile).first()
        investment_wallet = InvestmentWallet.objects.filter(user=user.profile).first()
        referral_wallet = ReferralWallet.objects.filter(user=user.profile).first()
        portfolio = int(main_wallet.overall_balance)  + investment_wallet.balance + referral_wallet.balance
        return portfolio
    return 0.00



