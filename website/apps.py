from django.apps import AppConfig
from django.db.models.signals import post_migrate
import sys

class WebsiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'website'

    def ready(self):
        import website.signals
        
        # Skip monitor startup during collectstatic
        if 'collectstatic' in sys.argv:
            return
            
        from website.services import SettingsService, MonitorService
        
        # Start monitors if auto-start is enabled
        if SettingsService.get_auto_start_monitors():
            try:
                MonitorService.control_monitor('icmp', 'start')
            except Exception as e:
                # Log the error but don't prevent server startup
                print(f"Failed to start ICMP monitor: {e}")