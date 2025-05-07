from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from apps.people.models import Member
from apps.people.serializers.belong import CheckMemberSerializer, SetPinSerializer, ResetPinSerializer
from apps.people.serializers.database import MemberSerializer
from apps.people.serializers.belong import BelongMemberSerializer

@api_view(["POST"])
@permission_classes([AllowAny])
def check_member_existence(request):
    data = request.data
    full_name = data.get("full_name", "").strip()
    date_of_birth = data.get("date_of_birth")

    if not full_name or not date_of_birth:
        return Response({"error": "Full name and date of birth are required."}, status=400)

    parts = full_name.split()
    if len(parts) < 2:
        return Response({"error": "Please provide both first name and last name."}, status=400)

    first_name, last_name = parts[0], parts[-1]

    member = Member.objects.filter(
        first_name__iexact=first_name,
        last_name__iexact=last_name,
        date_of_birth=date_of_birth
    ).first()

    if not member:
        return Response({ "Verification failed. Please try again." }, status=404)

    return Response({
        "member_key": member.member_key,
        "pin_set": member.pin_set,
        "full_name": member.full_name,
        "date_of_birth": member.date_of_birth,
    })

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_member_pin(request):
    serializer = CheckMemberSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    full_name = serializer.validated_data["full_name"].strip()
    pin = serializer.validated_data["access_pin"]
    date_of_birth = serializer.validated_data["date_of_birth"]

    parts = full_name.split()
    if len(parts) < 2:
        return Response({"error": "Please enter both first name and last name."}, status=400)
    
    first_name, last_name = parts[0], parts[-1]

    member = Member.objects.filter(
        first_name__iexact=first_name,
        last_name__iexact=last_name,
        date_of_birth=date_of_birth
    ).first()

    if not member:
        return Response("Verification failed. Please check your details and try again.", status=404)

    if member.verify_access_pin(pin):
        member_data = { "member_key": member.member_key, "id": member.id }
        return Response({"success": True, "member": member_data})
    else:
        return Response({"error": "Invalid PIN."}, status=403)


@api_view(["POST"])
@permission_classes([AllowAny])
def set_member_pin(request):
    serializer = SetPinSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    full_name = serializer.validated_data["full_name"]
    date_of_birth = serializer.validated_data["date_of_birth"]
    new_pin = serializer.validated_data["new_pin"]

    parts = full_name.split()
    if len(parts) < 2:
        return Response({
            "success": False,
            "message": "Please enter both first name and last name.",
            "status": 400
        }, status=400)

    first_name, last_name = parts[0], parts[-1]

    member = Member.objects.filter(
        first_name__iexact=first_name,
        last_name__iexact=last_name,
        date_of_birth=date_of_birth
    ).first()

    if not member:
        return Response({
            "success": False,
            "message": "Member not found.",
            "status": 404
        }, status=404)

    if member.pin_set:
        return Response({
            "success": False,
            "message": "PIN already set. Contact admin to reset.",
            "status": 403
        }, status=403)

    member.set_access_pin(new_pin)

    return Response({
        "success": True,
        "message": "PIN set successfully.",
        "status": 200
    }, status=200)
    

@api_view(["POST"])
@permission_classes([IsAdminUser])
def reset_member_pin(request):
    serializer = ResetPinSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    member_key = serializer.validated_data["member_key"]
    new_pin = serializer.validated_data["new_pin"]

    try:
        member = Member.objects.get(id=member_key)
        member.set_access_pin(new_pin)
        return Response({"success": f"PIN reset for {member.full_name}."})
    except Member.DoesNotExist:
        return Response({"error": "Member not found."}, status=404)


@api_view(["GET"])
@permission_classes([AllowAny]) 
def get_member_data(request, member_key):
    try:
        member = Member.objects.get(member_key=member_key)
        serializer = BelongMemberSerializer(member, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Member.DoesNotExist:
        return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)