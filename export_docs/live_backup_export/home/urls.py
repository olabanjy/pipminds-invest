from django.urls import path
from .views import * 
from django.contrib.auth.decorators import login_required

app_name = 'home' 

urlpatterns = [
    path('', login_required(Overview.as_view()), name='home'),

    path('terms-and-conditions/', t_and_c, name="t_and_c"),

    path('privacy/', privacy, name="privacy"),

    path('faqs/', faqs_in, name="faqs"),

    path('frequently-asked-questions/', faqs_out, name="frequently-asked-questions"),

    path('track-refund/', track_withdrawal_progress, name="track-refund"),

]
