from datetime import date
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from apps.analyzer.utils.assembly_analyzer import analyze_assembly_data
from apps.churches.models import Church
from apps.analyzer.serializers import AssemblyAnalysisSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analyze_data(request, assembly_id=None):
    year = int(request.query_params.get("year", date.today().year))
    upto_month = request.query_params.get("month")
    upto_month = int(upto_month) if upto_month else None

    if assembly_id:
        assembly = Church.objects.get(pk=assembly_id)
        data = analyze_assembly_data(assembly, year, upto_month)
        serializer = AssemblyAnalysisSerializer(instance=data)
        return Response(serializer.data)

    # For admin view (all assemblies)
    assemblies = Church.objects.all()
    results = [analyze_assembly_data(asm, year, upto_month) for asm in assemblies]
    serializer = AssemblyAnalysisSerializer(results, many=True)
    return Response(serializer.data)