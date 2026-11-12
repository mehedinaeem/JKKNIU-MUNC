from django.urls import path
from .views import CSRFTokenView, LoginView, LogoutView, CurrentAdministratorView

app_name = 'accounts'
urlpatterns = [
    path('admin/auth/csrf/', CSRFTokenView.as_view(), name='csrf'),
    path('admin/auth/login/', LoginView.as_view(), name='login'),
    path('admin/auth/logout/', LogoutView.as_view(), name='logout'),
    path('admin/auth/me/', CurrentAdministratorView.as_view(), name='me'),
]
