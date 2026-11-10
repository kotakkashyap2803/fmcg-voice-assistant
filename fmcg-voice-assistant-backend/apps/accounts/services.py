from django.contrib.auth import authenticate, get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class AuthenticationService:

    @staticmethod
    def authenticate_user(request, username=None, email=None, password=None):

        if email:
            users = User.objects.filter(
                email__iexact=email,
                is_active=True
            )

            if users.count() != 1:
                raise AuthenticationFailed(
                    "Invalid email or password."
                )

            username = users.first().username

        user = authenticate(
            request=request,
            username=username,
            password=password
        )

        if not user.is_staff:
            raise AuthenticationFailed(
                "You are not authorized to access the admin application."
            )

        if user is None:
            raise AuthenticationFailed(
                "Invalid username/email or password."
            )

        if not user.is_active:
            raise AuthenticationFailed(
                "Your account is inactive."
            )

        return user

    @staticmethod
    def generate_tokens(user):

        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def logout(refresh_token, user):

        try:
            token = RefreshToken(refresh_token)

            if str(token.payload.get("user_id")) != str(user.pk):
                raise AuthenticationFailed(
                    "You cannot revoke another user's token."
                )

            token.blacklist()

        except AuthenticationFailed:
            raise

        except Exception:
            raise AuthenticationFailed(
                "Invalid or expired refresh token."
            )