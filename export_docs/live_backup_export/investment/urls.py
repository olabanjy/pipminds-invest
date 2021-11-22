from django.urls import path, include 
from .views import * 
from django.contrib.auth.decorators import login_required

app_name = 'investment' 

urlpatterns = [

    path('', login_required(Dashboard.as_view()), name='dashboard'),
    path('update-kyc/', update_kyc, name='update-kyc'),
    path('kyc-pending-approval/', kyc_pending, name='kyc-pending'),
    path('kyc-rejected/', kyc_rejected, name='kyc-rejected'),
    path('plans/', login_required(InvestmentPlans.as_view()), name='plans'),
    path('process_plan/<plan_id>', login_required(ProcessInvestment.as_view()), name='process_plan'),

    path('rollover-plans/<inv_txn_code>', login_required(RolloverPlans.as_view()), name='rollover_plans'),

    path('process_rollover/<plan_id>/<inv_txn_code>', login_required(ProcessRollover.as_view()), name='process_rollover'),

    path('plan_details/<plan_id>', login_required(PlanDetails.as_view()), name='plan_details'),

    path('investment_successful/<plan_id>', investment_successful, name='investment_successful'),

    # path('cip_investment_contract/<plan_id>', cip_investment_contract_render_pdf_view, name="cip_investment_contract"),

    # path('hip_investment_contract/<plan_id>', cip_investment_contract_render_pdf_view, name="hip_investment_contract"),


    path('api/', include("investment.api.urls")),


    # path('test_add_value/', credit_cip_active_investments, name='add-value'),
    # path('test_add_value_hip/', credit_hip_active_investments, name='add-value-hip'),
    # path('complete-inv/', complete_inv_cycle, name='complete-inv'),


    # path('test_pdf/', GeneratePdf.as_view(), name='test_pdf'),


    #path('test_reminder/', generate_payment_for_completed_inv, name='test_reminder'),





]
