from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import HealthSerializer


class HealthView(APIView):
    """Public liveness probe; deliberately independent of database availability."""

    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        return Response(HealthSerializer({"status": "ok"}).data)
