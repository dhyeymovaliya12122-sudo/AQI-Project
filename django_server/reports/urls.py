# pyrefly: ignore [missing-import]
from django.urls import path
from . import views

urlpatterns = [
    path('',                  views.reports_list_create, name='report-list-create'),
    path('<uuid:pk>/',        views.get_report,          name='report-detail'),
    path('<uuid:pk>/vote/',   views.vote_report,         name='report-vote'),
    path('<uuid:pk>/delete/', views.delete_report,       name='report-delete'),
]
