from apps.church.models import Church
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import pagination, permissions, viewsets, status
from apps.church.serializers import ChurchSerializer, ChurchManagerSerializer
from apps.church.permissions import IsAdminUserOrOverseer


class StandardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000000


class ChurchView(viewsets.ModelViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class ChurchManagerView(viewsets.ModelViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchManagerSerializer
    # permission_classes = [IsAdminUserOrOverseer]
    permission_classes = [permissions.AllowAny]
    lookup_field = 'name'
    
    



                                

    
    
    




