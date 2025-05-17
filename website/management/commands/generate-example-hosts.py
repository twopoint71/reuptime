import random
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from website.models import Hosts

def random_account_name():
    prefix = ["Prod", "Dev", "Staging", "Backup"]
    suffix = ['mountain', 'brother', 'harmony', 'fortune', 'glacier', 'sunshine', 'library', 'journey', 'triangle', 'diamond',
              'freedom', 'whistle', 'notable', 'lantern', 'cabinet', 'pioneer', 'kingdom', 'network', 'passion', 'respect']
    return random.choice(prefix) + '-' + random.choice(suffix)

def random_account_id():
    return "".join(str(random.randint(0, 9)) for _ in range(12))

def random_region():
    return random.choice([
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        "af-south-1", "ap-east-1", "ap-south-1", "ap-south-2",
        "ap-southeast-1", "ap-southeast-2", "ap-southeast-3", "ap-southeast-4",
        "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
        "ca-central-1", "ca-west-1",
        "cn-north-1", "cn-northwest-1",
        "eu-central-1", "eu-central-2",
        "eu-west-1", "eu-west-2", "eu-west-3",
        "eu-north-1", "eu-south-1", "eu-south-2",
        "il-central-1",
        "me-central-1", "me-south-1",
        "sa-east-1",
        "us-gov-east-1", "us-gov-west-1"
    ])

def random_host_id():
    return f"i-{random.getrandbits(40):010x}"

def random_rfc1918_ip_address():
    block = random.choice(["10", "172", "192"])
    if block == "10":
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    elif block == "172":
        return f"172.{random.randint(16,31)}.{random.randint(0,255)}.{random.randint(1,254)}"
    else:
        return f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"

def random_host_name():
    return f"example.host-{random.randint(1000,9999)}"

def random_last_check():
    return datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 1440))

def random_is_active():
    return random.choices([True, False], weights=[8, 2])[0]

def random_is_monitored():
    return random.choices([True, False], weights=[7, 3])[0]

def random_downtime_allotment():
    return random.choices([30, 0, 10, 15], weights=[70, 10, 10, 10])[0]


class Command(BaseCommand):
    help = "Generate example Host records"

    def handle(self, *args, **kwargs):
        item_count = 10
        for _ in range(item_count):
            Hosts.objects.create(
                account_label=random_account_name(),
                account_id=random_account_id(),
                region=random_region(),
                host_id=random_host_id(),
                host_ip_address=random_rfc1918_ip_address(),
                host_name=random_host_name(),
                last_check=random_last_check(),
                is_active=random_is_active(),
                is_monitored=random_is_monitored(),
                downtime_allotment=random_downtime_allotment()
            )

        self.stdout.write(self.style.SUCCESS(f"✅ {item_count} example Hosts created."))
