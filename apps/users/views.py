from django.http import Http404
from rest_framework.response import Response
from apps.users.models import User, AuthHistory
from rest_framework import views, viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.users.serializers import (
    CustomTokenObtainPairSerializer,
    ListUserSerializer,
    ProfileSerializer,
    UniqueUserCheckSerializer,
    CreateUserSerializer,
    UserSerializer,
    AuthHistorySerializer,
    MinimalUserSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CreateUserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = [permissions.AllowAny]
    
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


class AssemblyAdminView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(church=self.request.user.church)  # type: ignore
    
    
    
from rest_framework.decorators import api_view
from rest_framework.response import Response

def get_user_by_email(email: str, request):
    email = email.strip().lower()

    if not email:
        return Response(
            {"error": "Email is required to proceed."},
            status=status.HTTP_400_BAD_REQUEST
        )

    allowed_domains = ["@cfi.church", "@cba.cfi.church"]
    if not any(email.endswith(domain) for domain in allowed_domains):
        return Response(
            {
                "error": (
                    "Unauthorized domain. Only users with @cfi.church or @cba.cfi.church "
                    "email addresses can log in."
                )
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = User.objects.filter(email__iexact=email).first()
    if user:
        return Response(
            {
                "message": "Email found. You can proceed to login.",
                "user": MinimalUserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK
        )

    return Response(
        {"error": "Email or username doesn't match any account"},
        status=status.HTTP_404_NOT_FOUND
    )

@api_view(["POST", "GET"])
def check_email(request):
    email = (
        request.data.get("email", "") if request.method == "POST" 
        else request.query_params.get("email", "")
    )
    return get_user_by_email(email, request)

    




    
    
    

