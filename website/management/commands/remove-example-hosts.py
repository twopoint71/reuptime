from django.core.management.base import BaseCommand
from website.models import Hosts

class Command(BaseCommand):
    help = "Remove example Host records"

    def handle(self, *args, **kwargs):
        example_host_count = Hosts.objects.filter(host_name__startswith="example.host-").count()
        Hosts.objects.filter(host_name__startswith="example.host-").delete()
        self.stdout.write(self.style.SUCCESS(f"✅ {example_host_count} example Hosts removed."))
