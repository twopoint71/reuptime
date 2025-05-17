import logging, os
from django.apps import AppConfig
from django.conf import settings

class MonitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitors'

    def ready(self):
        # Set up logging
        log_file = settings.APP_LOG_DIR / 'monitors.log'
        os.makedirs(settings.APP_LOG_DIR, exist_ok=True)

        # Configure logging
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '{levelname} {asctime} {module} {message}',
                    'style': '{',
                },
            },
            'handlers': {
                'file': {
                    'level': 'INFO',
                    'class': 'logging.FileHandler',
                    'filename': log_file,
                    'formatter': 'verbose',
                },
            },
            'loggers': {
                'monitors': {
                    'handlers': ['file'],
                    'level': 'INFO',
                    'propagate': True,
                },
            },
        })