from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Scheme
from .serializers import (
    SchemeSerializer,
    SchemeCalculationSerializer
)
from .services import SchemeService


class SchemeViewSet(viewsets.ModelViewSet):

    queryset = Scheme.objects.prefetch_related(
        "applicable_variants",
        "slabs"
    ).all()

    serializer_class = SchemeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        active = self.request.query_params.get("active")

        if active is not None:
            queryset = queryset.filter(
                is_active=active.lower() == "true"
            )

        scheme_type = self.request.query_params.get("type")

        if scheme_type:
            queryset = queryset.filter(scheme_type=scheme_type)

        return queryset


class SchemeCalculationView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = SchemeCalculationSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            result = SchemeService.calculate_offers(
                variant_id=serializer.validated_data["variant_id"],
                quantity=serializer.validated_data["quantity"]
            )

            return Response({
                "success": True,
                "data": result
            })

        except ValueError as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc)
                },
                status=status.HTTP_404_NOT_FOUND
            )