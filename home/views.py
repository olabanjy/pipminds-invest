from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, reverse, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.db.models import Sum
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.encoding import force_bytes
from users.models import * 
from investment.models import * 
from wallet.models import * 


class Overview(View):
    def get(self, request, *args, **kwargs):

        profile = Profile.objects.get(user=self.request.user)

        if not profile.profile_set_up:
            return redirect('users:profile-set-up')

        if not profile.investment_kyc_submitted:
            return redirect('investment:update-kyc')
        
        if profile.investement_verified == 'pending':
            print("KYC Pending")
            return redirect('investment:kyc-pending')
        elif profile.investement_verified == 'rejected':
            print("KYC Rejected")
            return redirect('investment:kyc-rejected')

        template = 'home/index.html' 
        
        dollar_rate = ExchangeRates.objects.filter(name='USD').first()
        
        user_total_invested_funds = UserInvestment.objects.filter(user=profile).aggregate(amount_sum=Sum("amount"))
        user_total_profit = UserInvestmentEarnings.objects.filter(user=profile).aggregate(amount_sum=Sum("amount"))
        

        portfolio = 0
        if user_total_invested_funds['amount_sum'] and user_total_profit['amount_sum'] != None:
            portfolio = user_total_invested_funds['amount_sum'] + user_total_profit['amount_sum']

        user_profits = UserInvestmentEarnings.objects.filter(user=profile, active=True).all()
        user_investments = UserInvestment.objects.filter(user=profile, active=True).all()

        withdraws = Withdrawal.objects.filter(user = self.request.user.profile).order_by('-id').all()
        deposits = Deposit.objects.filter(user = self.request.user.profile).order_by('-id').all()

        print(user_total_invested_funds['amount_sum'])
        print(user_total_profit['amount_sum'])
        print(user_investments)

        deposit_trans = None
        withdrawal_trans = None
        
        if deposits:
            deposit_trans = deposits[:4]
        if withdraws:
            withdrawal_trans = withdraws[:4]


        context = {
            'user_total_invested_funds': user_total_invested_funds['amount_sum'],
            'user_total_profit': user_total_profit['amount_sum'],
            'user_profits': user_profits,
            'user_investments': user_investments,
            'portfolio': portfolio,
            'dollar_rate_val': dollar_rate.rate_to_base, 
            'deposit_trans': deposit_trans,
            'withdrawal_trans' : withdrawal_trans
        }
        return render(self.request, template, context)

def t_and_c(request):

    template = 'home/terms_and_condition.html'

    return render(request, template)

def privacy(request):

    template = 'home/privacy.html'

    return render(request, template)

@login_required
def faqs_in(request):

    template = 'home/faqs_in.html'

    return render(request,template)

def faqs_out(request):

    template = 'home/faq_out.html'

    return render(request, template)

def trigger_error(request):
    division_by_zero = 1 / 0



def track_withdrawal_progress(request): 
    template = "home/withdrawal_status_approved.html"
    approved_withdrawals  = Withdrawal.objects.filter(status="approved", approved=True).all()
    pending_withdrawals  = Withdrawal.objects.filter(status="pending", approved=False).all()
    context = {
        'approved_withdrawals': approved_withdrawals,
        'pending_withdrawals':pending_withdrawals
    }

    return render(request, template, context)

