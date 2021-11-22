from django.urls import path, include
from .views import * 
from django.contrib.auth.decorators import login_required

app_name = 'wallet' 

urlpatterns = [
    path('', login_required(Dashboard.as_view()), name='dashboard'),

    path('wallets/', login_required(WalletsView.as_view()), name='wallets'),

    path('request-withdrawal/<wallet>', login_required(RequestWithdrawal.as_view()), name='withdraw'),

    path('withdrawal-request-sent/<transaction_code>', withdraw_request_sent, name='withdrawal-request-sent'),

    path('fund-account', login_required(DepositFunds.as_view()), name='deposit'),

    path('pay-with-card/<transaction_code>', login_required(PaystackPayment.as_view()), name='paystack-payment'),

    path('pay-with-monnify/<transaction_code>', login_required(MonifyPayment.as_view()), name='monify-payment'),

    path('pay-with-bank-deposit/<transaction_code>', login_required(BankTransferPayment.as_view()), name='manual-payment'),

    path('get-deposit-reference-code/<txn_code>/', get_manual_trans_code, name='get-ref-code'),

    path('bank-deposit-completed/<txn_code>/', payment_successful, name='payment-success'),

    path('card_deposit_complete/<txn_code>/', payment_successful_paystack, name='payment-success-paystack'),

    path('bank-transfer_complete/<txn_code>/', payment_successful_monnify, name='payment-success-monnify'),

    path('cancel_deposit/<transaction_code>', cancel_deposit, name='cancel-deposit'),

    path('cancel_user_withdrawal/<transaction_code>', cancel_user_withdrawal, name='cancel-user-withdrawal'),
    
    path('cancel_user_deposit/<transaction_code>', cancel_user_deposit, name='cancel-user-deposit'),

    path('check_balance/', check_balance, name='check_balance'),

    path('update_monnify_transRef/', update_monnify_transRef, name='update_monnify_transRef'),

    path('monnify_webhook_url/', monnify_test_webhook_view, name='monnify_webhook_url'),

    path('monnify_webhook_url_sandbox/', monnify_test_webhook_view_sandbox, name='monnify_webhook_url_sandbox'),

    path('api/', include("wallet.api.urls")), 
]