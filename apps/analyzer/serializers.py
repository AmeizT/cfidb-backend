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
    completion = serializers.IntegerField()
    rating = serializers.IntegerField()
    overdue = serializers.BooleanField()
    last_created_at = serializers.DateTimeField(allow_null=True)

class AssemblyAnalysisSerializer(serializers.Serializer):
    assembly = serializers.IntegerField()
    assembly_name = serializers.CharField()
    year = serializers.IntegerField()
    results = MonthAnalysisSerializer(many=True)
    summary = serializers.DictField(child=serializers.FloatField(), default={'average_completion': 0.0, 'average_rating': 0.0})