from django.urls import path, include 
from .views import * 
from django.contrib.auth.decorators import login_required

app_name = 'users' 

urlpatterns = [
    #ACCOUNT SET UP AND KYC
    path('profile-set-up/', login_required(CompleteProfile.as_view()), name='profile-set-up'),
    path('investment-set-up/', login_required(InvestmentKYC.as_view()), name='investment-set-up'),
    path('restart_personal_details/', restart_onboarding, name='restart_personal_details' ),
    path('check_sponsor/', check_sponsor, name='check_sponsor'),
    path('check_account_details/', check_account_details, name='check_account_details'),

    # PROFILE DASHBOARD URLS 
    path('', login_required(ProfileDashboard.as_view()), name='dashboard'),
    path('subscription/', login_required(MySubscription.as_view()), name='subscription'),
    path('subscription-detail/', login_required(PPPDetails.as_view()), name='subscription-detail'),
    path('update-subscription/<subscription_id>',updateSubscription , name='update-subscription'),
    path('cancel-subscription/',cancelSubscription , name='cancel-subscription'),

    #MANAGE REFERRAL TREE
    path('manage-referral/',login_required(ManageReferrals.as_view()) , name='manage-referral'),

    path('ppp-dashboard/',ppp_dashboard , name='ppp-dashboard'),

    path('ppp-onboarding/',ppp_onboarding , name='ppp-onboarding'),


    path('ppp-get-started/',ppp_get_started , name='ppp-get-started'),



    #ACCOUNT SETTINGS 
    path('profile-settings/',login_required(AccountSettings.as_view()) , name='profile-settings'),

    path('profile-preferences/',login_required(ProfilePreference.as_view()) , name='profile-preference'),

    path('activate-wallet-remit/', activate_wallet_remit , name='activate-wallet-remit'),

    path('deactivate-wallet-remit/', deactivate_wallet_remit , name='deactivate-wallet-remit'),

    path('api/', include("users.api.urls")), 





























    #MIGRATIONS URLS ------------ STAY OFF 

    # path('admin-import/', ADMIN_USER_IMPORT.as_view() , name='admin-import'),

    # path('send-ppp-email/', SendPPPEmail.as_view() , name='send-ppp-email'),


    # path('cip-import/', CIP_USER_IMPORT.as_view() , name='cip-import'),

    # path('cip-user-assign/', CIP_ASSIGN_SPONSOR.as_view() , name='cip-user-assign'),

    # path('check-multiple-sponsor/',check_multiple_sponsor, name='check-multiple-sponsor' ),

    # path('get-cip-investors/',get_cip_investors, name='get-cip-investors' ),

    # path('get-cip-users-only/',get_cip_users_only, name='get-cip-users-only'),

    # path('hip-import/', HIP_USER_IMPORT.as_view() , name='hip-import'),

    # path('hip-user-assign/', HIP_ASSIGN_SPONSOR.as_view() , name='hip-user-assign'),


    # path('send-cip-email/', SendCIPEmail.as_view() , name='send-cip-email'),


    # path('clear-ppp-earnings/', clear_ppp_earnings , name='clear-ppp-earnings'),

    # path('get-cip-users-only/',get_cip_payout, name='get-cip-users-only'),

    path('get-cip-users-only/',get_toped_up_inv_with_sponsors, name='get-cip-users-only'),

    path('get_specific_investment_type_by_date/',get_specific_investment_type_by_date, name='get_specific_investment_type_by_date'),


    #  path('credit-missed-payout/', CreditMissedPayouts.as_view() , name='credit-missed-payout'),

    path('unused_funds/', get_total_uninvested_wallet , name="unused_funds"),

    # path('import_top_ups/', ImportTopUps.as_view() , name='import_top_ups'),

    # path('top_up_balance/', TopupBalance.as_view() , name='top_up_balance'),

    # path('get_pay_to_wallet/', get_all_paytowallet , name='get_pay_to_wallet'),

    # path('get_all_false_ended_investment/', get_all_false_ended_investment , name='get_all_false_ended_investment'),



    # path('process_rollover/', CIP_ROLLOVER.as_view() , name='process_rollover'),

    # path('fix_celery/', correct_celery_lag , name='fix_celery'),


    # path('fix_earn/', correct_celery_lag_daily , name='fix_earn')

    # path('fix_ppp/', get_all_pioneers , name='fix_ppp'),

    path('get_all_partners/', get_all_partners , name='get_all_partners'),

    #path('process_cip_capital_refund/', process_cip_capital_refund , name='process_cip_capital_refund')

    path('custom_query/', CheckUserSponsor.as_view() , name='custom_query'),

    path('verify_email/', ValidateEmail.as_view() , name='verify_email'),

]