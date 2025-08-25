from rest_framework import serializers

class MonthAnalysisSerializer(serializers.Serializer):
    month = serializers.CharField()
    tithes = serializers.BooleanField()
    income = serializers.BooleanField()
    expenditure = serializers.BooleanField()
    attendance = serializers.BooleanField()
    tithes_comment = serializers.CharField()
    income_comment = serializers.CharField()
    expenditure_comment = serializers.CharField()
    attendance_comment = serializers.CharField()
    completion_percentage = serializers.IntegerField()
    stars = serializers.IntegerField()
    overdue = serializers.BooleanField()

class AssemblyAnalysisSerializer(serializers.Serializer):
    assembly = serializers.IntegerField()
    assembly_name = serializers.CharField()
    year = serializers.IntegerField()
    data = MonthAnalysisSerializer(many=True)
    summary = serializers.DictField()