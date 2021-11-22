from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


class ProfileAdmin(admin.ModelAdmin):
    search_fields = ('first_name', 'user_code', 'user__email', 'phone', )
    list_display = ['first_name', 'user_code', 'user']
    list_filter = ['first_name', 'user_code', 'user']


class ReferralAdmin(admin.ModelAdmin):
    search_fields = ('sponsor__user__email', 'downline__user__email', )

class UserBankAccountAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', 'account_name', 'account_number' )


class NotificationsAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

class NextOfKinAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

class UserDocumentAdmin(admin.ModelAdmin):
    search_fields = ('user__user__email', )

class UserMembershipAdmin(admin.ModelAdmin):
    search_fields = ('user__email', )


class MyUserAdmin(UserAdmin):

    ordering = ('date_joined', )
  
    list_display = ('username', 'email', 'date_joined', 'last_login')

admin.site.register(Profile, ProfileAdmin)
admin.site.register(UserBankAccount, UserBankAccountAdmin)
admin.site.register(NextOfKin, NextOfKinAdmin)
admin.site.register(Referral)
admin.site.register(UserReferrals, ReferralAdmin)
admin.site.register(UserDocument, UserDocumentAdmin)

admin.site.register(Membership)
admin.site.register(UserMembership, UserMembershipAdmin)
admin.site.register(Subscription)
admin.site.register(SubscriptionInstance)


admin.site.register(UserNotifications, NotificationsAdmin)
admin.site.register(SupportTickets)
admin.site.register(UserImportDoc)


admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)

