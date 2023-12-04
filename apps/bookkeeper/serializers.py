from apps.bookkeeper.models import (
    Asset, 
    Income, 
    Expenditure, 
    FixedExpenditure, 
    Payroll, 
    Pledge, 
    Tithe
)
from rest_framework import serializers
from apps.people.serializers import MemberSerializer

        
class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'
        
    
class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = '__all__'


class FixedExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedExpenditure
        fields = '__all__'
        
        
class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = '__all__'
            

class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = '__all__'     


class PledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pledge
        fields = '__all__' 

class TitheSerializer(serializers.ModelSerializer):
    member = MemberSerializer()
    class Meta:
        model = Tithe
        fields = [
            'id', 
            'branch', 
            'member', 
            'amount', 
            'payment_method', 
            'receipt', 
            'timestamp',
            'created_at', 
            'updated_at'
        ]
        
        
class CreateTitheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tithe
        fields = '__all__'