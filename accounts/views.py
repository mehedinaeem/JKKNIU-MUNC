from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token, rotate_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from registrations.parsers import BoundedJSONParser
from .roles import can_access_administration
from .serializers import LoginSerializer, administrator_data
from .throttles import limit_login


def csrf_failure(request, reason=''):
    return JsonResponse({'detail': 'CSRF verification failed. Refresh the CSRF token and try again.'}, status=403)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'csrf_token': get_token(request)})


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [BoundedJSONParser]

    @sensitive_variables('serializer', 'data')
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        limit_login(request, data['username'])
        user = authenticate(request=request._request, username=data['username'], password=data['password'])
        if user is None or not can_access_administration(user):
            return Response({'detail': 'Invalid administrator credentials.'}, status=401)
        login(request._request, user)
        return Response({'authenticated': True, 'administrator': administrator_data(user),
                         'csrf_token': get_token(request)})


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request._request)
        rotate_token(request)
        return Response(status=204)


class CurrentAdministratorView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        authenticated = can_access_administration(request.user)
        return Response({'authenticated': authenticated,
                         'administrator': administrator_data(request.user) if authenticated else None})
