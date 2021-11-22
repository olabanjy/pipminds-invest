from rest_framework import status
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from investment.models import * 
from investment.api.serializers import * 
from users.api.pagination import MyDefaultSetPagination


class InvestmentPlansAPIView(APIView):
    def get(self, request):
        investment_plans = InvestmentPlan.objects.filter(active=True).all()
        serializer = InvestmentPlanSerializer(investment_plans, many=True)
        return Response(serializer.data)

class InvestmentPlansDetailAPIView(APIView):
    def get_object(self, pk):
        investment_plan = get_object_or_404(InvestmentPlan, pk=pk)
        return investment_plan

    def get(self, request, pk):
        investment_plan = self.get_object(pk)
        serializer = InvestmentPlanSerializer(investment_plan)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        investment_plan = self.get_object(pk)
        serializer = InvestmentPlanSerializer(investment_plan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class UserInvestmentListCreateAPIView(APIView):
#     def get(self, request):
#         user_investments = UserInvestment.objects.filter(active=True)
#         serializer = UserInvestmentSerializer(user_investments, many=True)
#         return Response(serializer.data)  

class UserInvestmentListCreateAPIView(generics.ListAPIView):
    queryset = UserInvestment.objects.filter(active=True, completed = False).order_by("-id")
    serializer_class = UserInvestmentSerializer
    pagination_class = MyDefaultSetPagination   

class UniqueUserInvestmentAPIView(APIView):
    def get(self, request, user_code):
        user_investments = UserInvestment.objects.filter(user__user_code=user_code).all()
        serializer = UserInvestmentSerializer(user_investments, many=True)
        return Response(serializer.data)     
        


class UserInvestmentDetailAPIView(APIView):
    def get_object(self, txn_code):
        user_investment = get_object_or_404(UserInvestment, txn_code=txn_code)
        return user_investment

    def get(self, request, txn_code):
        user_investment = self.get_object(txn_code)
        serializer = UserInvestmentSerializer(user_investment)
        return Response(serializer.data)



class UserInvestmentEarningsAPIView(APIView):
    def get(self, request):
        user_investments_earnings = UserInvestmentEarnings.objects.filter(active=True).all()
        serializer = UserInvestmentEarningsSerializer(user_investments_earnings, many=True)
        return Response(serializer.data) 



