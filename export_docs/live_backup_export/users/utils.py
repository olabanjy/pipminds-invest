from .models import *
from django.contrib.auth.models import User
import requests
import datetime
import pytz
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.core.files.base import ContentFile
from django.core.files import File

from xhtml2pdf import pisa


def get_user_membership(request):
    user_membership_qs = UserMembership.objects.filter(user=request.user)
    if user_membership_qs.exists():
        return user_membership_qs.first()
    return None

# def get_user_referrals(sponsor):
#     referrals_qs = UserReferrals.objects.filter(sponsor=sponsor)
#     if referrals_qs.exists():
#         return referrals_qs.all()
#     return None

# def get_user_referrals(sponsor):
#     referrals_qs = UserReferrals.objects.filter(sponsor=sponsor)
#     if referrals_qs.exists():
#         for child in referrals_qs.all():
#             profile = child.downline
#             return profile
#     return None

# def get_user_wallet_balance(request):
#     wallet_balance_qs = Wallet.objects.filter(user=request.user)
#     if wallet_balance_qs.exists():
#         return wallet_balance_qs.first()
#     return None


def get_user_subscription(request):
    user_subscription_qs = Subscription.objects.filter(
        user_membership=get_user_membership(request))
    if user_subscription_qs.exists():
        user_subscription = user_subscription_qs.first()
        return user_subscription
    return None


def get_selected_membership(request):
    membership_type = request.session['selected_membership_type']
    selected_membership_qs = Membership.objects.filter(
        membership_type=membership_type)
    if selected_membership_qs.exists():
        return selected_membership_qs.first()
    return None


def time_of_day():
    cur_time = datetime.datetime.now(tz=pytz.timezone(str(settings.TIME_ZONE)))
    if cur_time.hour < 6:
        return 'Dawn'
    elif 6 <= cur_time.hour < 12:
        return 'Morning'
    elif 12 <= cur_time.hour < 16:
        return 'Afternoon' 
    elif 16 <= cur_time.hour < 19:
        return 'Evening'
    else:
        return 'Night'



# def send_welcome_email(request, user):
#     subject, from_email, to = 'Welcome', 'helpdesk@imaginariumng.com', [
#         user.email]
#     text_content = f" Dear {user.username}. Welcome to Ultra ! "
#     html_content = render_to_string(
#         'account/email/welcome_email.html', {'username': user.username})
#     msg = EmailMultiAlternatives(subject, text_content, from_email, to)
#     msg.attach_alternative(html_content, "text/html")
#     msg.send()


# def send_welcome_email(user_id):
#     user =  User.objects.get(pk=user_id)
#     subject, from_email, to = 'Welcome', 'helpdesk@imaginariumng.com', [
#         user.email]
#     text_content = f" Dear {user.username}. Welcome to Ultra ! "
#     html_content = render_to_string(
#         'account/email/welcome_email.html', {'username': user.username})
#     msg = EmailMultiAlternatives(subject, text_content, from_email, to)
#     msg.attach_alternative(html_content, "text/html")
#     msg.send()



def new_render_to_file_ppp_sub(template_src, filename, sub_id, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    sub = SubscriptionInstance.objects.get(txn_code=sub_id)
    print(sub.user)
    if not pdf.err:
        with open(filename, 'wb+') as output:
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), output)
            sub.contract_file.save(filename, output)
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None 