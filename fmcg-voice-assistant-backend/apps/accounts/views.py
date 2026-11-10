from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import LoginSerializer, UserSerializer
from .services import AuthenticationService


class HealthCheckView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "success": True,
            "message": "FMCG Voice Agent backend is running.",
            "data": {
                "service": "fmcg-voice-agent-api",
                "status": "healthy"
            }
        })


class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthenticationService.authenticate_user(
            request=request,
            username=serializer.validated_data.get("username"),
            email=serializer.validated_data.get("email"),
            password=serializer.validated_data["password"]
        )

        tokens = AuthenticationService.generate_tokens(user)

        return Response({
            "success": True,
            "message": "Login successful.",
            "data": {
                "user": UserSerializer(user).data,
                "tokens": tokens
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({
                "success": False,
                "message": "Refresh token is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        AuthenticationService.logout(
            refresh_token=refresh_token,
            user=request.user
        )

        return Response({
            "success": True,
            "message": "Logout successful."
        }, status=status.HTTP_200_OK)


class CurrentUserView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        return Response({
            "success": True,
            "message": "User details retrieved successfully.",
            "data": UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)