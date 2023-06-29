from apps.church.models import Church
from rest_framework import serializers
from apps.demographics.models import Attendance, Members
from apps.finance.models import Expenditure, Income, Asset


class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'
        
        
class AttendnaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        
        
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Members
        fields = '__all__'
        
        
class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = '__all__'
        
        
class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = '__all__'
        
        
class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'
        
        
class ChurchManagerSerializer(serializers.ModelSerializer):
    assets = AssetSerializer(many=True, read_only=True)
    attendance = AttendnaceSerializer(many=True, read_only=True)
    expenditure = ExpenditureSerializer(many=True, read_only=True)
    income = IncomeSerializer(many=True, read_only=True)
    members = MemberSerializer(many=True, read_only=True)
    
    class Meta:
        model = Church
        fields = [
            'church_id', 
            'name', 
            'desc',
            'address',
            'town',
            'province',
            'country',
            'code',
            'phone',
            'email',
            'created_at',
            'updated_at',
            'assets',
            'attendance',
            'expenditure',
            'income',
            'members'
        ]  


        
            

        
        

        
        
