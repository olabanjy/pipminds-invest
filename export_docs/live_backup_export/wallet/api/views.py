from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from django.contrib.auth.models import User
from users.models import * 
from wallet.api.serializers import * 
from wallet.models import *
from wallet.tasks import *



class MainWalletAPIView(APIView):
    def get(self, request):
        main_wallet = MainWallet.objects.all()
        serializer = MainWalletSerializer(main_wallet, many=True)
        return Response(serializer.data)

class MainWalletDetailView(APIView):
    def get_object(self, user_code):
        wallet = MainWallet.objects.filter(user__user_code=user_code).first()
        return wallet

    def get(self, request, user_code):
        wallet = self.get_object(user_code)
        serializer = MainWalletSerializer(wallet)
        return Response(serializer.data)


    def patch(self, request, user_code):
        wallet = self.get_object(user_code)
        serializer = MainWalletSerializer(wallet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InvestmentWalletDetailView(APIView):
    def get_object(self, user_code):
        wallet = InvestmentWallet.objects.filter(user__user_code=user_code).first()
        return wallet

    def get(self, request, user_code):
        wallet = self.get_object(user_code)
        serializer = InvestmentWalletSerializer(wallet)
        return Response(serializer.data)


    def patch(self, request, user_code):
        wallet = self.get_object(user_code)
        serializer = InvestmentWalletSerializer(wallet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReferralWalletDetailView(APIView):
    def get_object(self, user_code):
        wallet = ReferralWallet.objects.filter(user__user_code=user_code).first()
        return wallet

    def get(self, request, user_code):
        wallet = self.get_object(user_code)
        serializer = ReferralWalletSerializer(wallet)
        return Response(serializer.data)


    def patch(self, request, user_code):
        wallet = self.get_object(user_code)
        serializer = ReferralWalletSerializer(wallet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingDepositsAPIView(APIView):
    def get(self, request):
        deposits = Deposit.objects.filter(status="pending").all()
        serializer = DepositSerializer(deposits, many=True)
        return Response(serializer.data)

class DepositsAPIView(APIView):
    def get(self, request):
        deposits = Deposit.objects.all()
        serializer = DepositSerializer(deposits, many=True)
        return Response(serializer.data)



# MAINTENANCE - COMPLETE - 23/02/2021
class DepositDetailAPIView(APIView):

    def get_object(self, txn_code):
        deposit = get_object_or_404(Deposit, txn_code=txn_code)
        return deposit

    def get(self, request, txn_code):
        deposit = self.get_object(txn_code)
        serializer = DepositSerializer(deposit)
        return Response(serializer.data)


    def patch(self, request, txn_code):
        deposit = self.get_object(txn_code)
        print(request.data['status'])
        serializer = DepositSerializer(deposit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if request.data['status'] == "approved":
                profile = deposit.user
                
                amount_deposited = deposit.amount 
                user_wallet = MainWallet.objects.filter(user=profile).first()
                user_wallet.deposit += int(amount_deposited)
                user_wallet.save()

                the_trans = Transaction.objects.filter(txn_code=deposit.txn_code).first()
                the_trans.approved = True
                the_trans.save()

                manual_deposit_approved.delay(profile.user.pk, txn_code)

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, txn_code):
        deposit = self.get_object(txn_code)
        deposit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class PendingWithdrawalsAPIView(APIView):
    def get(self, request):
        withrawals = Withdrawal.objects.filter(status="pending").all()
        serializer = WithdrawalSerializer(withrawals, many=True)
        return Response(serializer.data)

class WithdrawalsDetailAPIView(APIView):

    def get_object(self, txn_code):
        withdrawal = get_object_or_404(Withdrawal, txn_code=txn_code)
        return withdrawal

    def get(self, request, txn_code):
        withdrawal = self.get_object(txn_code)
        serializer = WithdrawalSerializer(withdrawal)
        return Response(serializer.data)


    def patch(self, request, txn_code):
        withdrawal = self.get_object(txn_code)
        print(request.data['status'])
        serializer = WithdrawalSerializer(withdrawal, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if request.data['status'] == "approved":
                profile = withdrawal.user
                withdrawal_request_approved.delay(profile.user.pk, txn_code)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, txn_code):
        withdrawal = self.get_object(txn_code)
        withdrawal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class UniqueUserDepositsAPIView(APIView):
    def get(self, request, user_code):
        user_deposits = Deposit.objects.filter(user__user_code=user_code).all()
        serializer = DepositSerializer(user_deposits, many=True)
        return Response(serializer.data) 


class UniqueUserWithrawalsAPIView(APIView):
    def get(self, request, user_code):
        user_withrawals = Withdrawal.objects.filter(user__user_code=user_code).all()
        serializer = WithdrawalSerializer(user_withrawals, many=True)
        return Response(serializer.data)

class CIPPaymentAPIView(APIView):
    def get(self, request):
        payments = Payments.objects.filter(status='pending',remark__contains="CIP ROI").all()
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

class HIPPaymentAPIView(APIView):
    def get(self, request):
        payments = Payments.objects.filter(status='pending',remark__contains="HIP ROI").all()
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class PaymentDetailAPIView(APIView):

    def get_object(self, txn_code):
        payment = get_object_or_404(Payments, txn_code=txn_code)
        return payment

    def get(self, request, txn_code):
        payment = self.get_object(txn_code)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)


    def patch(self, request, txn_code):
        payment = self.get_object(txn_code)
        serializer = PaymentSerializer(payment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, txn_code):
        payment = self.get_object(txn_code)
        payment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulkApprovePaymentDetailAPIView(APIView):
    def put(self, request, the_date):
        payments = Payments.objects.filter(created_at__date=the_date).all()
        print(payments)
        instances = []
        for payment in payments:
            payment.approved = True
            payment.status = "approved"
            payment.save()
            instances.append(payment)
        
        serializer = PaymentSerializer(instances, many=True)
        return Response(serializer.data)
        