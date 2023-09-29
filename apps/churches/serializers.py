from apps.churches.models import Church
from rest_framework import serializers
from apps.people.models import Attendance, Member
from apps.bookkeeper.models import Asset, Expenditure, Income, Payroll


class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'
        
        
class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        
      
class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'
              
        
class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = '__all__'
        
        
class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = '__all__'
        
               
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'
        
        
class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = '__all__'
        
        
class ChurchTrackerSerializer(serializers.ModelSerializer):
    assets = AssetSerializer(many=True, read_only=True)
    attendance = AttendanceSerializer(many=True, read_only=True)
    expenditure = ExpenditureSerializer(many=True, read_only=True)
    income = IncomeSerializer(many=True, read_only=True)
    members = MemberSerializer(many=True, read_only=True)
    payroll = PayrollSerializer(many=True, read_only=True)
    
    class Meta:
        model = Church
        fields = (
            'id',
            'church_id', 
            'name', 
            'description',
            'address',
            'city',
            'province',
            'country',
            'code',
            'lang',
            'currency',
            'phone',
            'email',
            'avatar',
            'banner',
            'brand',
            'assets',
            'attendance',
            'expenditure',
            'income',
            'members',
            'payroll',
            'created',
            'updated',
        ) 


        
            

        
        

        
        
