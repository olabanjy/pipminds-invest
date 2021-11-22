from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import *
import requests



class ProfileSetUpForm(forms.Form):
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',

    }))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg'
        
    }))
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={
        
        'class': 'form-control form-control-lg'
    }))
    dob = forms.DateField(required=True, widget=forms.DateInput(attrs={
        
        'class': 'form-control form-control-lg',
        'type': 'date',
        'placeholder': 'mm/dd/yyyy'
    }))
    address_1 = forms.CharField(required=True, widget=forms.TextInput(attrs={
        
        'class': 'form-control form-control-lg'
    }))

    address_2 = forms.CharField(required=False, widget=forms.TextInput(attrs={
        
        'class': 'form-control form-control-lg'
    }))

    city = forms.CharField(required=True, widget=forms.TextInput(attrs={
        
        'class': 'form-control form-control-lg'
    }))

    state = forms.CharField(required=True, widget=forms.TextInput(attrs={
        
        'class': 'form-control form-control-lg'
    }))
    
    nationality = CountryField(blank_label='(select country)').formfield(required=True, widget=CountrySelectWidget(attrs={
        'class': 'form-control form-control-lg '
    }))

    zip_code = forms.CharField(required=False, widget=forms.TextInput(attrs={
        
        'class': 'form-control form-control-lg'
    }))

    ref_code = forms.CharField(required=False, widget=forms.TextInput(attrs={
        
        'class': 'form-control form-control-lg',
        'id': 'ref_code', 
        'onInput': 'checkSponsor()'
    }))

  
    
    t_and_c = forms.BooleanField(required=True, widget=forms.CheckboxInput(attrs={
        'class': 'custom-control-input',
        'id': 'tc-agree'
    }))

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        ref_code = cleaned_data.get('ref_code')
        first_name = cleaned_data.get('first_name')
        try:
            if ref_code:
                sponsor = Profile.objects.filter(user_code=ref_code).first()
                if not sponsor:
                    raise forms.ValidationError(" Sponsor with referral code does not exist!")
            if phone:
                user_exists = Profile.objects.filter(phone=phone).first()
                if user_exists and user_exists.first_name != first_name:
                    raise forms.ValidationError(" A User with that phone number already exists! ")
                
            return cleaned_data


        except (ValueError, NameError, TypeError, ImportError, IndexError ) as error:
            err_msg = str(error)
            raise forms.ValidationError(err_msg)
            return cleaned_data
            print(err_msg)




NUBAN_API_KEY = "NUBAN-AUHVFBOQ292"


PASSPORT = 0
NATIONAL_ID = 1
DRIVING_LICENSE = 2
DOC_TYPE = (
    (PASSPORT, 'Passport'),
    (DRIVING_LICENSE, 'Driving License'),
    (NATIONAL_ID, 'National ID'),
)
class InvestmentKYCForm(forms.Form):
    bank_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'id': 'bank_name',
        'disabled': True

    }))

    
    account_name = forms.CharField(required=True,  widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'id': 'acct_name',
        'disabled': True

    }))
    account_number = forms.CharField(required=True, min_length=10, max_length=10, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'id': 'acct_num'
        

    }))
    swift_code = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Optional'

    }))

    document_front = forms.FileField(required=True, widget=forms.FileInput( attrs={
        'id':'id_front',
        'accept': 'file_extension|.pdf, .jpg, .png, .jpeg',
        'class': 'kyc_file'
    }))
    document_back = forms.FileField(required=False, widget=forms.FileInput( attrs={
        'id':'id_back',
        'accept': 'file_extension|.pdf, .jpg, .png, .jpeg',
        'class': 'kyc_file'
    }))

    doc_type = forms.ChoiceField(choices=DOC_TYPE, widget=forms.RadioSelect())
   
    next_of_kin_fullname = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',

    }))

    next_of_kin_email = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Optional'

    }))

    next_of_kin_phone = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        
    }))


    t_and_c = forms.BooleanField(required=True, widget=forms.CheckboxInput(attrs={
        'class': 'custom-control-input',
        'id': 'tc-agree'
    }))

    def clean(self):
        cleaned_data = super().clean()
        document_front = cleaned_data.get('document_front')
        document_back = cleaned_data.get('document_back')
        account_number = cleaned_data.get('account_number')
        account_name = cleaned_data.get('account_name')
        
        
        try:
            if document_front:
                if not document_front.name.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    raise forms.ValidationError("Wrong File format, must be .pdf or .png or .jpg")
                if document_front.size > 5242880:
                    raise forms.ValidationError(f"File is too large. Size should not be more than 1MB")
            
            if document_back:
                if not document_back.name.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    raise forms.ValidationError("Wrong File format, must be .pdf or .png or .jpg")
                if document_back.size > 5242880:
                    raise forms.ValidationError("File is too large. Size should not be more than 1MB")
                
            if account_number:
                account_exists = UserBankAccount.objects.filter(account_number=account_number).first()
                if account_exists:
                    raise forms.ValidationError("A User with that account number already exists!")
            
            if account_name:
                account_name_new = account_name.lower()
                print(account_name_new)
                check_current_accounts = UserBankAccount.objects.filter(account_name__contains=account_name_new)
                print(check_current_accounts)
                if check_current_accounts:
                    raise forms.ValidationError(f"A User with that account details already exists!")

                
            return cleaned_data


        except (ValueError, NameError, TypeError, ImportError, IndexError ) as error:
            err_msg = str(error)
            raise forms.ValidationError(err_msg)
            return cleaned_data
            print(err_msg)

        



class UpdateProfileForm(forms.Form):
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Enter First name', 
        'id': 'first-name'

    }))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
       'class': 'form-control form-control-lg',
        'placeholder': 'Enter Last name', 
        'id': 'last-name'
        
    }))
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Phone Number',
        'id': 'phone-no'
    }))

    dob = forms.DateField(required=True, widget=forms.DateInput(attrs={
        'class': 'form-control form-control-lg date-picker',
        'id': 'birth-day'
    }))

class UpdateAddressForm(forms.Form):
    address_1 = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg', 
        'id': 'address-l1'
    }))

    address_2 = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg', 
         'id': 'address-l2'
    }))

    state = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg', 
         'id': 'address-st'
    }))

    nationality = CountryField(blank_label='select country').formfield(required=True, widget=CountrySelectWidget(attrs={
        'class': 'form-control form-control-lg ', 
        'id': 'address-county'
       
    }))


class ImportUserForm(forms.Form):
    document = forms.FileField(required=False, widget=forms.FileInput( attrs={
        'id':'id_back',
        'accept': 'file_extension|.csv'
    }))
