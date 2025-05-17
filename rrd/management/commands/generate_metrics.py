from django.core.management.base import BaseCommand
from django.conf import settings
from rrd.services import RRDService
import logging
import time
import random
from pathlib import Path
import rrdtool
from website.models import Hosts

logger = logging.getLogger('rrd')

class Command(BaseCommand):
    help = 'Generate example metrics for existing RRD files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours of data to generate (default: 24)'
        )

    def round_to_next_interval(self, timestamp, interval=30):
        """Round up to the next interval"""
        return ((timestamp + interval - 1) // interval) * interval

    def get_last_update(self, rrd_path):
        """Get the last update time from RRD file"""
        try:
            return rrdtool.last(str(rrd_path))
        except Exception as e:
            logger.error(f"Failed to get last update time for {rrd_path}: {str(e)}")
            return None

    def generate_metrics(self, host_id, hours):
        """Generate metrics for a specific host"""
        rrd_path = settings.RRD_DIR / f"{host_id}.rrd"
        service = RRDService()

        if not rrd_path.exists():
            logger.info(f"RRD file not found for host {host_id}, creating new file")
            try:
                service.create_rrd_file(host_id)
                logger.info(f"Created new RRD file for host {host_id}")
            except Exception as e:
                logger.error(f"Failed to create RRD file for host {host_id}: {str(e)}")
                return

        # Get the last update time
        last_update = self.get_last_update(rrd_path)
        if last_update is None:
            logger.error(f"Failed to get last update time for {rrd_path}")
            return

        # Calculate start time (next interval after last update)
        print(last_update)
        start_time = self.round_to_next_interval(last_update + 1)

        # Calculate end time
        end_time = int(time.time())

        # Calculate number of intervals
        interval = 30  # 30 second intervals
        num_intervals = (end_time - start_time) // interval

        # Limit to requested hours
        max_intervals = (hours * 3600) // interval
        num_intervals = min(num_intervals, max_intervals)

        if num_intervals <= 0:
            logger.warning(f"No new intervals to generate for host {host_id}")
            return

        logger.info(f"Generating {num_intervals} intervals for host {host_id}")

        # Generate and update metrics
        for i in range(num_intervals):
            current_time = start_time + (i * interval)

            # Generate realistic metrics
            # Uptime: 95-100% with occasional drops
            uptime = random.uniform(95, 100)
            if random.random() < 0.05:  # 5% chance of downtime
                uptime = random.uniform(0, 94)

            # Latency: 50-200ms with occasional spikes
            latency = random.uniform(50, 200)
            if random.random() < 0.1:  # 10% chance of high latency
                latency = random.uniform(200, 2000)

            try:
                service.update_rrd_file(host_id, uptime, latency)
                logger.debug(f"Updated metrics for host {host_id} at {current_time}")
            except Exception as e:
                logger.error(f"Failed to update metrics for host {host_id}: {str(e)}")
                break

    def handle(self, *args, **options):
        hours = options['hours']

        # Query the database for example hosts
        hosts = Hosts.objects.filter(host_name__startswith='example.host-')

        if not hosts.exists():
            self.stdout.write(self.style.WARNING('No example hosts found in database'))
            return

        # Generate metrics for each example host
        for host in hosts:
            self.stdout.write(f'Generating metrics for host {host.host_name} (UUID: {host.uuid})...')
            self.generate_metrics(host.uuid, hours)

        self.stdout.write(self.style.SUCCESS('Successfully generated example metrics'))