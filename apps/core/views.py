from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework import permissions, viewsets
from apps.core.models import Blog, Documentation, TermsAndConditions, UserTermsAcceptance
from apps.core.serializers import (
    BlogSerializer, 
    DocumentationSerializer, 
    TermsAndConditionsSerializer
)

class DocumentationView(viewsets.ModelViewSet):
    queryset = Documentation.objects.all()
    serializer_class = DocumentationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        """Automatically set the author to the logged-in user."""
        serializer.save(author=self.request.user)

class BlogView(viewsets.ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

class TermsView(viewsets.ModelViewSet):
    queryset = TermsAndConditions.objects.all()
    serializer_class = TermsAndConditionsSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class TermsCheckView(APIView):
    """Check if the user has accepted the latest active terms."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        latest_terms = TermsAndConditions.objects.filter(is_active=True).order_by('-created_at').first()

        if not latest_terms:
            return Response({"message": "No terms available."}, status=status.HTTP_204_NO_CONTENT)

        has_accepted = UserTermsAcceptance.objects.filter(user=user, terms=latest_terms).exists()

        return Response({
            "has_accepted": has_accepted,
            "terms": TermsAndConditionsSerializer(latest_terms).data
        })


class AcceptTermsView(APIView):
    """Allow a user to accept the latest terms."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        latest_terms = TermsAndConditions.objects.filter(is_active=True).order_by('-created_at').first()

        if not latest_terms:
            return Response({"error": "No active terms to accept."}, status=status.HTTP_400_BAD_REQUEST)

        already_accepted = UserTermsAcceptance.objects.filter(user=user, terms=latest_terms).exists()
        if already_accepted:
            return Response({"message": "Terms already accepted."}, status=status.HTTP_400_BAD_REQUEST)

        UserTermsAcceptance.objects.create(user=user, terms=latest_terms, accepted_at=now())

        return Response({"message": "Terms accepted successfully."}, status=status.HTTP_200_OK)
