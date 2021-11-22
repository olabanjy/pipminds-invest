
from django import forms
from .models import *



PAYPAL = 0
CREDIT_CARD = 1
MANUAL_TRANSFER = 2
MONNIFY = 3
TNX_TYPE = (
    (PAYPAL, 'PAYPAL'),
    (CREDIT_CARD, 'CREDIT CARD'),
    (MANUAL_TRANSFER, 'MANUAL TRANSFER'),
    (MONNIFY, 'MONNIFY'),
)

DESTINATION = (
    ('bank', 'BANK ACCOUNT'),
    ('flex_wallet', 'FLEX WALLET'),

)


class DepositForm(forms.Form):
    amount = forms.IntegerField(required=True, widget=forms.NumberInput(attrs={
        'class': 'form-control form-control-lg form-control-number',
        'id': 'buysell-amount', 
        'onInput': 'showTxnTypes()'
    }))

    txn_type = forms.ChoiceField(choices=TNX_TYPE, widget=forms.RadioSelect())
    
class WithdrawalForm(forms.Form):
    amount = forms.IntegerField(required=True, widget=forms.NumberInput(attrs={
        'class': 'form-control form-control-lg form-control-number',
        'id': 'buysell-amount', 
        'onInput': 'checkBalance()'
       
    }))
    destination = forms.ChoiceField(required=False, choices=DESTINATION, widget=forms.Select(attrs={
        'class':'form-control form-control-lg',
        'id': 'destination'
    }))

class DepositProofForm(forms.Form):
    proof_file = forms.FileField(required=True, widget=forms.FileInput())
