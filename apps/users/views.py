from django.http import Http404
from rest_framework.response import Response
from apps.users.models import User, AuthHistory
from rest_framework import views, viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.users.serializers import (
    CustomTokenObtainPairSerializer,
    ListUserSerializer,
    AccountSerializer,
    UniqueUserCheckSerializer,
    CreateUserSerializer,
    UserSerializer,
    AuthHistorySerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CreateUserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
      
    
class UniqueUserCheckView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UniqueUserCheckSerializer
    permission_classes = [permissions.AllowAny] 
            
class RetrieveUserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = ListUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['head', 'get', 'put', 'patch']
    
    def get_object(self):
        return self.request.user

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    

class UserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['head', 'get', 'put', 'patch']
    
    # def get_object(self):
    #     return self.request.user

    # def list(self, request, *args, **kwargs):
    #     return self.retrieve(request, *args, **kwargs)
    

class ListUsersView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['head', 'get',]
    

class AuthHistoryView(viewsets.ModelViewSet):
    queryset = AuthHistory.objects.all()
    serializer_class = AuthHistorySerializer
    permission_classes = [permissions.AllowAny]
    
    
    

    
    
    

