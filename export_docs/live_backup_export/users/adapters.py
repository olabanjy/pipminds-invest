# from allauth.account.adapter import DefaultAccountAdapter


# class MyAccountAdapter(DefaultAccountAdapter):
#     def clean_password(self, password):
#         if re.match(r'^(?=.*?\d)(?=.*?[A-Z])(?=.*?[a-z])[A-Za-z\d]{8,}$', password):
#             return password
#         else:
#             raise ValidationError("Password must be at least 8 characters with 1 uppercase letter and 1 number")