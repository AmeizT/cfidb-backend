from django.http import Http404
from apps.users.models import User, Account
from rest_framework.response import Response
from rest_framework import views, viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.users.serializers import (
    CustomTokenObtainPairSerializer,
    ListUserSerializer,
    AccountSerializer,
    UniqueUserCheckSerializer,
    CreateUserSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CreateUserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    
    def get_object(self):
        return self.request.user

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    
    # def post(self, request):
    #     serializer = UserSerializer(data=request.data)
    #     if serializer.is_valid():
    #         user = serializer.save()
    #         if user:
    #             return Response({'message': 'created'}, status=status.HTTP_201_CREATED)
    #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
      
    
class UniqueUserCheckView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UniqueUserCheckSerializer
    permission_classes = [permissions.AllowAny] 
    
    

class AccountView(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.AllowAny] 
      
        
class RetrieveUserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = ListUserSerializer
    
    def get_object(self):
        return self.request.user

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    

# class CreateUserView(viewsets.ModelViewSet):
#     permission_classes = [permissions.AllowAny]
#     queryset = User.objects.all()
#     serializer_class = ListUserSerializer
#     http_method_names = ['post', 'put', 'patch']
    
    
    

    
    
    

