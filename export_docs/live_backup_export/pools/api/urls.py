# from django.urls import path
# from investment.api.views import * 


# urlpatterns = [

#     path('active_investment_plans/', InvestmentPlansAPIView.as_view(), name="active_investment_plans"),


#     path('active_investment_plans/<int:pk>/', InvestmentPlansDetailAPIView.as_view(), name="active_investment_plan_details"),


#     path('active_user_investments/', UserInvestmentListCreateAPIView.as_view(), name="active_user_investments"),


#     path('unique_user_investments/<user_code>/', UniqueUserInvestmentAPIView.as_view(), name="unique_user_investments"),

    

#     path("active_user_investments/<txn_code>/", UserInvestmentDetailAPIView.as_view(), name="active_user_investments_detail"),

#      path('active_user_investment_earnings/', UserInvestmentEarningsAPIView.as_view(), name="active_user_investment_earnings"),

# ]