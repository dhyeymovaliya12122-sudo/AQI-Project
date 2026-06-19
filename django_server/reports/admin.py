# pyrefly: ignore [missing-import]
from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display  = ('id', 'type', 'severity', 'status', 'lat', 'lng', 'created_at')
    list_filter   = ('status', 'type', 'severity')
    search_fields = ('description', 'type')
    ordering      = ('-created_at',)
