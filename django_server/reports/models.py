import uuid
# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
from django.conf import settings


def apply_decay(report):
    age_hours = (timezone.now() - report.created_at).total_seconds() / 3600
    return age_hours >= settings.REPORT_EXPIRY_HOURS or report.downvotes >= settings.DOWNVOTE_HIDE_THRESHOLD


class Report(models.Model):
    POLLUTION_TYPES = [
        ('smoke', 'Smoke'), ('chemical', 'Chemical'),
        ('dust', 'Dust'), ('noise', 'Noise'), ('other', 'Other'),
    ]
    STATUS_CHOICES = [('active', 'Active'), ('expired', 'Expired')]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lat         = models.FloatField()
    lng         = models.FloatField()
    type        = models.CharField(max_length=20, choices=POLLUTION_TYPES)
    severity    = models.IntegerField()
    description = models.TextField(blank=True, default='')
    image_url   = models.URLField(blank=True, null=True)
    upvotes     = models.IntegerField(default=0)
    downvotes   = models.IntegerField(default=0)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at  = models.DateTimeField(auto_now_add=True)
    user        = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lat', 'lng']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'Report({self.type}, sev={self.severity}, {self.status})'

    def check_and_apply_decay(self):
        if self.status == 'active' and apply_decay(self):
            self.status = 'expired'
            self.save(update_fields=['status'])
        return self
