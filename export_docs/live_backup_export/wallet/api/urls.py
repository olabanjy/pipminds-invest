from django.urls import path
from wallet.api.views import * 

urlpatterns = [
    path('main-wallets/',MainWalletAPIView.as_view(),name="main-wallets"),

    path('main-wallet-details/<user_code>/', MainWalletDetailView.as_view(), name="main-wallet-details" ),

    path('investment-wallet-details/<user_code>/', InvestmentWalletDetailView.as_view(), name="investment-wallet-details" ),

    path('referral-wallet-details/<user_code>/', ReferralWalletDetailView.as_view(), name="referral-wallet-details" ),

    path('deposits/', DepositsAPIView.as_view(), name="deposits"),

    path('pending-deposits/', PendingDepositsAPIView.as_view(), name="pending-deposits"),

    path('approve-deposit/<txn_code>/', DepositDetailAPIView.as_view(), name="approve-deposit"),

    path('pending-withrawals/', PendingWithdrawalsAPIView.as_view(), name="pending-withdrawals"), 

    path('approve-withdrawal/<txn_code>/', WithdrawalsDetailAPIView.as_view(), name="approve-withdrawal"),


    path('unique_user_deposits/<user_code>/', UniqueUserDepositsAPIView.as_view(), name="unique-user-deposits"),

    path('unique_user_withrawals/<user_code>/', UniqueUserWithrawalsAPIView.as_view(), name="unique-user-withrawals"),

    path('cip-payouts/', CIPPaymentAPIView.as_view(), name="cip-payouts"),

    path('approve_bulk_payout/<the_date>/', BulkApprovePaymentDetailAPIView.as_view(), name="approve_bulk_payout"),

    path('hip-payouts/', HIPPaymentAPIView.as_view(), name="hip-payouts"),

    path('payout/<txn_code>/', PaymentDetailAPIView.as_view(), name="payout-detaiil"),

         ]