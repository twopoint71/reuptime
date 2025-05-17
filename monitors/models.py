from django.db import models
import uuid

class MonitorStatus(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    monitor_type = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('stopped', 'Stopped')
    ])
    pid = models.IntegerField(null=True, blank=True)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Monitor Statuses"

    def __str__(self):
        return f"{self.monitor_type} - {self.status}"