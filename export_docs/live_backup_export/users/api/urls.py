from django.urls import path
from users.api.views import * 


urlpatterns = [
    path('profiles/', 
         ProfileSerializerListCreateAPIView.as_view(), 
         name="profiles"),
    
     path('referrals/', 
         ReferralsView.as_view(), 
         name="referrals"),

     path('referrals/<user_code>/', 
         UniqueReferralsView.as_view(), 
         name="unique-referrals"),
    

    path('users/', 
         UserSerializerListCreateAPIView.as_view(), 
         name="users"),

    path('profiles/<user_code>/', 
          ProfileDetailAPIView.as_view(),
          name="profile-detail"), 

    path('pending_kyc/', PendingKYCView.as_view(), name="pending-kyc"), 

    path('partners/', PartnersView.as_view(), name="partners"), 

    path('user_bank_details/<user_code>/',UserBankAccountDetailAPIView.as_view(), name="user_bank_details" ),

    path('user_next_of_kin/<user_code>/', UserNextOfKinDetailAPIView.as_view(), name="user_next_of_kin" ),

    path('user_search_handler/<user_email>/', GeneralUserSearchHandlerView.as_view(), name="user_search_handler"),

    path('cip_roi_report/<the_date>/', cip_report, name="cip_roi_report")
   
]