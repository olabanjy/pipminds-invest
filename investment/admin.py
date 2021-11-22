from django.contrib import admin
from .models import *




class UserInvestmentAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email','txn_code')

    ordering = ('pk', )
  
    list_display = ('pk', 'txn_code', 'user', 'created_at', 'active', 'completed', 'plan', 'next_payout')

class UserInvestmentEarningsAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

    list_display = (  'user', 'created_at', 'plan',  'amount')

class UserInvestmentTopUpAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

class UserInvestmentRolloverAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )



admin.site.register(InvestmentPeriod)
admin.site.register(InvestmentCategory)
admin.site.register(InvestmentPlan)
admin.site.register(UserInvestment, UserInvestmentAdmin)
admin.site.register(UserInvestmentEarnings, UserInvestmentEarningsAdmin)
admin.site.register(ExchangeRates)
admin.site.register(UserInvestmentRollovers, UserInvestmentRolloverAdmin)
admin.site.register(CapitalPaybacks)
admin.site.register(UserInvestmentTopups, UserInvestmentTopUpAdmin)