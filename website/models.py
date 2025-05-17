import uuid
from django.db import models

# Create your models here.
class Hosts(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    account_label = models.TextField(null=True, blank=True)
    account_id = models.TextField(null=True, blank=True)
    region = models.TextField(null=True, blank=True)
    host_id = models.TextField(null=True, blank=True)
    host_ip_address = models.TextField(null=True, blank=True)
    host_name = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_check = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_monitored = models.BooleanField(default=True)
    downtime_allotment = models.IntegerField(default=0)
    last_allotment_reset = models.DateTimeField(auto_now_add=True)
    monitor_type = models.TextField(null=True, blank=True)
    monitor_params = models.TextField(null=True, blank=True)

class GlobalSettings(models.Model):
    key = models.CharField(primary_key=True, max_length=255)
    value = models.IntegerField()
    description = models.TextField(null=True, blank=True)
