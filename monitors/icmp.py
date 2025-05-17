import subprocess
import platform
import time
import logging
import multiprocessing
import signal
import sys
from django.conf import settings
from website.models import Hosts
from rrd.services import RRDService
import statistics
from datetime import datetime

logger = logging.getLogger('monitors')

class ICMPMonitor:
    def __init__(self):
        self.rrd_service = RRDService()
        self.timeout = 2000  # 2000ms timeout

    def ping_host(self, host):
        """Ping a single host and return (is_active, latency)"""
        try:
            # Different ping commands for different OS
            if platform.system().lower() == "windows":
                ping_cmd = ['ping', '-n', '1', '-w', str(self.timeout), host.host_ip_address]
            else:
                ping_cmd = ['ping', '-c', '1', '-W', str(self.timeout // 1000), host.host_ip_address]

            result = subprocess.run(ping_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                # Extract latency from output
                if platform.system().lower() == "windows":
                    # Windows format: "time=123ms"
                    latency_str = result.stdout.split("time=")[-1].split("ms")[0]
                else:
                    # Unix format: "time=123.456 ms"
                    latency_str = result.stdout.split("time=")[-1].split(" ms")[0]

                try:
                    latency = round(float(latency_str), 4)
                    return True, latency
                except ValueError:
                    logger.error(f"Failed to parse latency for host {host.host_name}: {latency_str}")
                    return False, 0
            else:
                return False, 0

        except Exception as e:
            logger.error(f"Error pinging host {host.host_name}: {str(e)}")
            return False, 0

    def update_host_status(self, host, is_active, latency):
        """Update host status in database and RRD"""
        try:
            # If the host is down, check and update downtime allotment
            if not is_active:
                original_allotment = host.downtime_allotment or 0

                if original_allotment > 0:
                    # Use up 30 seconds of allotment, but keep host up even if it hits zero
                    new_allotment = max(0, original_allotment - 30)
                    host.downtime_allotment = new_allotment
                    logger.info(
                        f"Host {host.host_name} is DOWN, using downtime allotment ({original_allotment} -> {new_allotment}). Not marking as down yet."
                    )
                    is_active = True  # Keep host up for this run
                else:
                    # Allotment is already zero, mark host as down
                    logger.info(
                        f"Host {host.host_name} is DOWN. Downtime allotment depleted. Marking as down."
                    )

            # Update database
            host.is_active = is_active
            host.last_check = datetime.now()
            host.save()

            # Update RRD
            self.rrd_service.update_rrd_file(host.uuid, 100 if is_active else 0, latency)

            logger.info(
                f"Updated host {host.host_name}: active={is_active}, latency={latency}ms, downtime_allotment={host.downtime_allotment}"
            )
        except Exception as e:
            logger.error(f"Failed to update host {host.host_name}: {str(e)}")

    def run(self):
        """Run the ICMP monitor"""
        logger.info("Starting ICMP monitor run")

        # Get all monitored hosts
        hosts = Hosts.objects.filter(is_monitored=True)
        if not hosts.exists():
            logger.warning("No monitored hosts found")
            return

        # Create a pool of workers
        with multiprocessing.Pool() as pool:
            # Ping all hosts in parallel
            results = pool.map(self.ping_host, hosts)

        # Process results
        active_hosts = []
        latencies = []

        for host, (is_active, latency) in zip(hosts, results):
            self.update_host_status(host, is_active, latency)

            if is_active:
                active_hosts.append(1)
                latencies.append(latency)

        # Calculate aggregate metrics
        total_hosts = len(hosts)
        active_count = len(active_hosts)

        if total_hosts > 0:
            uptime_percentage = round((active_count / total_hosts) * 100, 4)
            avg_latency = round(statistics.mean(latencies) if latencies else 0, 4)
        else:
            uptime_percentage = 0
            avg_latency = 0

        # Update monitor's RRD file
        try:
            self.rrd_service.update_rrd_file('monitors_aggregate_icmp', uptime_percentage, avg_latency)
            logger.info(f"Updated monitor metrics: uptime={uptime_percentage}%, avg_latency={avg_latency}ms")
        except Exception as e:
            logger.error(f"Failed to update monitor metrics: {str(e)}")

        logger.info("Completed ICMP monitor run")

    # Add before the run_monitor function
    def signal_handler(signum, frame):
        """Handle termination signals"""
        logger.info("Received termination signal, shutting down...")
        sys.exit(0)

    # Update the run_monitor function
    def run_monitor():
        """Entry point for the monitor daemon"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        monitor = ICMPMonitor()
        while True:
            try:
                monitor.run()
                time.sleep(30)  # Wait 30 seconds before next run
            except Exception as e:
                logger.error(f"Monitor run failed: {str(e)}")
                time.sleep(30)  # Wait before retrying


def run_monitor():
    """Entry point for the monitor daemon"""
    monitor = ICMPMonitor()
    while True:
        try:
            monitor.run()
            time.sleep(30)  # Wait 30 seconds before next run
        except Exception as e:
            logger.error(f"Monitor run failed: {str(e)}")
            time.sleep(30)  # Wait before retrying

if __name__ == '__main__':
    run_monitor()