from datetime import datetime, timezone
from typing import Dict, Any, List
from django.conf import settings
from django.forms.models import model_to_dict
from django.contrib import messages
from collections import deque
import os
import psutil

from website.models import Hosts, GlobalSettings
from rrd.services import RRDService
from monitors.models import MonitorStatus
from monitors.management.commands.monitor_icmp import Command

class HostService:
    @staticmethod
    def get_monitored_hosts() -> List[Hosts]:
        return Hosts.objects.filter(is_monitored=1).order_by("is_active")

    @staticmethod
    def get_host_count() -> int:
        return Hosts.objects.count()

    @staticmethod
    def get_monitored_active_count() -> int:
        return Hosts.objects.filter(is_monitored=1, is_active=1).count()
    
    @staticmethod
    def get_monitored_inactive_count() -> int:
        return Hosts.objects.filter(is_monitored=1, is_active=0).count()

    @staticmethod
    def get_monitored_has_allotment_count() -> int:
        return Hosts.objects.filter(is_monitored=1, downtime_allotment__gt=0).count()
    
    @staticmethod
    def get_monitored_has_no_allotment_count() -> int:
        return Hosts.objects.filter(is_monitored=1, downtime_allotment=0).count()

    @staticmethod
    def get_unmonitored_hosts() -> List[Hosts]:
        return Hosts.objects.filter(is_monitored=0).order_by("host_name")
    
    @staticmethod
    def update_host_monitoring_status(uuid: str, is_monitored: bool) -> None:
        host = Hosts.objects.get(uuid=uuid)
        host.is_monitored = is_monitored
        host.save()
        return host

    @staticmethod
    def update_host_settings(uuid: str, host_data: Dict[str, str]) -> None:
        host = Hosts.objects.get(uuid=uuid)
        for key, value in host_data.items():
            setattr(host, key, value)
        host.save()
        return host
    
    @staticmethod
    def delete_host(host_uuid: str) -> Hosts:
        host = Hosts.objects.get(uuid=host_uuid)
        host.delete()
        rrd = RRDService()
        rrd.destroy_rrd_file(host.uuid)
        return host
    
    @staticmethod
    def create_host(host_data: Dict[str, str]) -> tuple[Hosts | None, str]:
        # Check if host already exists
        existing_host = Hosts.objects.filter(
            region=host_data['region'],
            host_ip_address=host_data['host_ip_address']
        ).first()
        
        if existing_host:
            return None

        # if downtime_allotment is not set, use the default downtime allotment
        if host_data['downtime_allotment'] == '':
            settings = GlobalSettings.objects.filter(key='default_downtime_allotment').first()
            default_allotment = int(settings.value) if settings else 0
            host_data['downtime_allotment'] = default_allotment

        host = Hosts.objects.create(**host_data)
        rrd = RRDService()
        rrd.create_rrd_file(host.uuid)
        return host
    
class MonitorService:
    @staticmethod
    def get_monitor_status(monitor_type: str) -> Dict[str, Any]:
        status = MonitorStatus.objects.get(monitor_type=monitor_type)
        current_time = datetime.now(timezone.utc)
        
        return {
            **model_to_dict(status),
            'uptime': (current_time - status.last_active).total_seconds(),
            'last_active': status.last_active.isoformat()
        }

    @staticmethod
    def control_monitor(monitor_type: str, action: str) -> None:
        if monitor_type != 'icmp':
            raise ValueError(f"Invalid monitor type: {monitor_type}")
            
        monitor = Command()
        if action == 'stop':
            monitor.stop_monitor()
        elif action == 'start':
            monitor.start_monitor()
        elif action == 'refresh':
            monitor.show_status()
        else:
            raise ValueError(f"Invalid action: {action}")

class LogService:
    @staticmethod
    def get_log_content(log_type: str, log_tail: int) -> str:
        log_file = f"{settings.APP_LOG_DIR}/{log_type}.log"
        
        if not os.path.exists(log_file):
            raise FileNotFoundError("Log file not found")
            
        with open(log_file, "r") as file:
            return ''.join(line for line in deque(file, maxlen=log_tail))

class SystemService:
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        current_time = datetime.now(timezone.utc)
        return {
            'monitored_hosts': Hosts.objects.filter(is_monitored=True).count(),
            'unmonitored_hosts': Hosts.objects.filter(is_monitored=False).count(),
            'total_hosts': Hosts.objects.count(),
            'server_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'server_uptime': (current_time - datetime.fromtimestamp(psutil.boot_time(), timezone.utc)).total_seconds(),
        }

class SettingsService:
    @staticmethod
    def get_default_downtime_allotment() -> str:
        return GlobalSettings.objects.filter(key="default_downtime_allotment").first().value
    
    @staticmethod
    def update_default_downtime_allotment(value: str) -> None:
        GlobalSettings.objects.filter(key="default_downtime_allotment").update(value=value)

    @staticmethod
    def get_auto_start_monitors() -> bool:
        setting = GlobalSettings.objects.filter(key="auto_start_monitors").first()
        return bool(int(setting.value)) if setting else False
    
    @staticmethod
    def update_auto_start_monitors(value: bool) -> None:
        GlobalSettings.objects.filter(key="auto_start_monitors").update(value=int(value))