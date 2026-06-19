# pyrefly: ignore [missing-import]
from django.contrib import admin
# pyrefly: ignore [missing-import]
from django.urls import path, include
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.utils import timezone


def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'AQI Civic Action Hub — Dhyey API Gateway (Django)',
        'timestamp': timezone.now().isoformat(),
        'framework': 'Django REST Framework',
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check),
    path('api/auth/', include('reports.auth_urls')),
    path('api/reports/', include('reports.urls')),
    path('api/analytics/', include('analytics.urls')),
]
