from rest_framework import serializers
from apps.finance.models import Asset, Income, Expenditure, Payroll



        
class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'
        
    
class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = '__all__'

class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = '__all__'
            

class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = '__all__'     
