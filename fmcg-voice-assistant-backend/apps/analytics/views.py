from django.shortcuts import render

# Create your views here.
from datetime import date

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.analytics.services import AnalyticsService


class DashboardAnalyticsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Only staff members can access business analytics.
        if not request.user.is_staff:
            return Response({
                "success": False,
                "message": "You do not have permission to access analytics."
            }, status=status.HTTP_403_FORBIDDEN)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        try:
            if start_date:
                start_date = date.fromisoformat(start_date)

            if end_date:
                end_date = date.fromisoformat(end_date)

        except ValueError:
            return Response({
                "success": False,
                "message": "Dates must use YYYY-MM-DD format."
            }, status=status.HTTP_400_BAD_REQUEST)

        if start_date and end_date and start_date > end_date:
            return Response({
                "success": False,
                "message": "start_date cannot be later than end_date."
            }, status=status.HTTP_400_BAD_REQUEST)

        data = AnalyticsService.get_dashboard(
            start_date=start_date,
            end_date=end_date
        )

        return Response({
            "success": True,
            "message": "Dashboard analytics retrieved successfully.",
            "data": data
        }, status=status.HTTP_200_OK)