from django.urls import path, include 
from .views import * 
from django.contrib.auth.decorators import login_required

app_name = 'pools' 

urlpatterns = [

     path('', login_required(ExplorePools.as_view()), name='explore'),
     path('wallet/', login_required(PoolsWalletsView.as_view()), name='wallet'),
     path('mypools/', login_required(MyPoolInvestments.as_view()), name='mypools'),



]