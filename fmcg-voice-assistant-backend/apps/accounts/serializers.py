from django.contrib.auth import get_user_model
from rest_framework import serializers


User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=False,
        allow_blank=False
    )

    email = serializers.EmailField(
        required=False
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False
    )

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")

        if not username and not email:
            raise serializers.ValidationError(
                "Provide either username or email."
            )

        if username and email:
            raise serializers.ValidationError(
                "Provide username or email, not both."
            )

        return attrs


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_superuser",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()