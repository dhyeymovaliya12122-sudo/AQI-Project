# pyrefly: ignore [missing-import]
from django.urls import path
# pyrefly: ignore [missing-import]
from . import views

urlpatterns = [
    path('heatmap/', views.heatmap, name='analytics-heatmap'),
    path('stats/',   views.stats,   name='analytics-stats'),
    path('cdi/',     views.cdi,     name='analytics-cdi'),
]
