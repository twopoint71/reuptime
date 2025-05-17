from django.core.management.base import BaseCommand
from django.conf import settings
from rrd.services import RRDService
import logging

logger = logging.getLogger('rrd')

class Command(BaseCommand):
    help = 'Initialize RRD database files for all hosts'

    def handle(self, *args, **options):
        try:
            service = RRDService()
            service.initialize_all_rrd_files()
            self.stdout.write(self.style.SUCCESS('Successfully initialized RRD files'))
        except Exception as e:
            logger.error(f"Failed to initialize RRD files: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Failed to initialize RRD files: {str(e)}'))