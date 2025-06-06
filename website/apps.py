from django.apps import AppConfig
from django.db.models.signals import post_migrate
import sys

class WebsiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'website'

    def ready(self):
        import website.signals
        
        # Skip monitor startup during collectstatic or migrations
        if 'collectstatic' in sys.argv or 'makemigrations' in sys.argv or 'migrate' in sys.argv:
            return
            
        # Defer the imports and monitor startup to avoid early database access
        def start_monitors(sender, **kwargs):
            from website.services import SettingsService, MonitorService
            
            # Start monitors if auto-start is enabled
            if SettingsService.get_auto_start_monitors():
                try:
                    MonitorService.control_monitor('icmp', 'start')
                except Exception as e:
                    print(f"Failed to start ICMP monitor: {e}")

        # Connect to post_migrate signal to ensure database is ready
        post_migrate.connect(start_monitors, sender=self)