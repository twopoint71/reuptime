# myapp/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import GlobalSettings

@receiver(post_migrate)
def add_default_setting(sender, **kwargs):
    GlobalSettings.objects.get_or_create(
        key='default_downtime_allotment',
        defaults={
            'value': 30,
            'description': 'Default bi-weekly downtime allotment for hosts'
        }
    )
