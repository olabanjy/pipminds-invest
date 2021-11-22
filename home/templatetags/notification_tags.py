from django import template
from users.models import UserNotifications
from decimal import Decimal
from wallet.models import Deposit, Transaction

register = template.Library()


@register.filter
def user_notification(user):
    if user.is_authenticated:
        notifications = UserNotifications.objects.filter(user=user.profile).order_by('-id').all()[:10]
        return notifications
    return None

@register.filter
def user_pending_deposit(user):
    if user.is_authenticated:
        user_last_pending = Deposit.objects.filter(status="awaiting_proof", approved=False, user=user.profile).last()
        if user_last_pending:
            check_last_trans = Transaction.objects.get(txn_code=user_last_pending.txn_code)
            if check_last_trans.txn_method == "manual":
                return user_last_pending.txn_code
            return None
        return None
    return None



