# pyrefly: ignore [missing-import]
from django.urls import path
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import register, login

urlpatterns = [
    path('register/', register,                      name='auth-register'),
    path('login/',    login,                         name='auth-login'),
    path('refresh/',  TokenRefreshView.as_view(),    name='auth-refresh'),
]
