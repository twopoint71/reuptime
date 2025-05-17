import os
import time
import rrdtool
from django.conf import settings
import logging
import math
from pathlib import Path
from website.models import Hosts

logger = logging.getLogger("rrd")

class RRDService:
    def __init__(self):
        self.rrd_dir = settings.RRD_DIR
        self.step = 30  # 30 second collection frequency
        self.heartbeat = 60  # 2x step for heartbeat

        # Ensure RRD directory exists
        os.makedirs(self.rrd_dir, exist_ok=True)

        # Define RRA configurations
        self.rra_config = [
            # 30 second resolution (24 hours worth)
            f"RRA:AVERAGE:0.5:30s:2880",    # 2880 points = 24 hours of 30-second data
            # 1 minute resolution (24 hours worth)
            f"RRA:AVERAGE:0.5:1m:1440",     # 1440 points = 24 hours of 1-minute data
            # 5 minute resolution (7 days worth)
            f"RRA:AVERAGE:0.5:5m:2016",     # 2016 points = 7 days of 5-minute data
            # 1 hour resolution (30 days worth)
            f"RRA:AVERAGE:0.5:1h:720",      # 720 points = 30 days of hourly data
            # 1 day resolution (90 days worth)
            f"RRA:AVERAGE:0.5:1d:365",      # 365 points = 90 days of daily data
            # 1 week resolution (2 years worth)
            f"RRA:AVERAGE:0.5:1w:104",      # 104 points = 2 years of weekly data
            # 1 month resolution (5 years worth)
            f"RRA:AVERAGE:0.5:1M:60",      # 60 points = 5 years of monthly data
        ]

    def aligned_time(self, timestamp):
        seconds_past_minute = timestamp % 60
        base_minute = timestamp - seconds_past_minute
        return int(base_minute + (30 if seconds_past_minute >= 30 else 0))

    def get_rrd_path(self, host_id):
        """Get the path for a host RRD file"""
        return self.rrd_dir / f"{host_id}.rrd"

    def create_rrd_file(self, host_id):
        """Create a new RRD file for a host"""
        rrd_path = self.get_rrd_path(host_id)

        if rrd_path.exists():
            logger.warning(f"RRD file already exists for host {host_id}")
            return

        try:
            rrdtool.create(
                str(rrd_path),
                f"--step", str(self.step),
                f"--start", str(self.aligned_time(time.time() - 60)),
                # Data Sources
                f"DS:uptime:GAUGE:{self.heartbeat}:0:100",
                f"DS:latency:GAUGE:{self.heartbeat}:0:2000",
                # Round Robin Archives
                *self.rra_config
            )
            logger.info(f"Created RRD file for host {host_id}")
        except Exception as e:
            logger.error(f"Failed to create RRD file for host {host_id}: {str(e)}")
            raise

    def update_rrd_file(self, host_id, uptime, latency):
        """Update RRD file with new metrics"""
        rrd_path = self.get_rrd_path(host_id)

        if not rrd_path.exists():
            logger.warning(f"RRD file not found for host {host_id}, creating new file")
            self.create_rrd_file(host_id)

        try:
            current_time = self.aligned_time(time.time())
            last_update = rrdtool.last(str(rrd_path))

            # Ensure we are not updating in the past
            if current_time <= last_update:
                logger.warning(f"Update time {current_time} is not after last update {last_update}")
                return

            rrdtool.update(
                str(rrd_path),
                f"{current_time}:{uptime}:{latency}"
            )
            logger.info(f"Updated RRD file for host {host_id}")
        except Exception as e:
            logger.error(f"Failed to update RRD file for host {host_id}: {str(e)}")
            raise

    def initialize_all_rrd_files(self):
        """Initialize RRD files for all hosts"""
        host_uuid_list = Hosts.objects.all().values_list("uuid", flat=True)
        for host_uuid in host_uuid_list:
            self.create_rrd_file(host_uuid)

    def get_metrics(self, rrd_file, time_range_resolution_code=1):
        """
        Get metrics from RRD file for a specific resolution

        Args:
            rrd_file (str): The RRD file to get metrics for
            time_range_resolution_code (int): 0-n

        Returns:
            dict: Dictionary of raw RRD data
        """
        rrd_path = self.get_rrd_path(rrd_file)

        if not rrd_path.exists():
            message = f"RRD file not found for host {rrd_file}"
            logger.error(message)
            return { "error": message }

        trrc_map = [
            ["-15minutes", "30"],       # 30 seconds
            ["-1hour", "60"],           # 1 minute
            ["-3hours", "300"],         # 5 minutes
            ["-1days", "3600"],         # 1 hour
            ["-3days", "3600"],         # 1 hour
            ["-1months", "86400"],      # 1 day
            ["-1years", "604800"]       # 1 week
        ]

        # ensure time_range_resolution_code is an integer
        time_range_resolution_code = int(time_range_resolution_code)
        
        if 0 < time_range_resolution_code > len(trrc_map):
            message = f"Invalid time range resolution code: {time_range_resolution_code} valid range is 0-{len(trrc_map)-1}"
            logger.error(message)
            return { "error": message }

        start_time, resolution = trrc_map[time_range_resolution_code]

        # for now, end_time is always now
        end_time = self.aligned_time(time.time())
        
        logger.info(f"Start time: {start_time}, Resolution: {resolution}, End time: {end_time}, time_range_resolution_code: {time_range_resolution_code}")
        try:
            # Fetch data from RRD
            return rrdtool.fetch(
                str(rrd_path),
                "AVERAGE",
                "--start", str(start_time),
                "--end", str(end_time),
                "--resolution", str(resolution),
                "--align-start"
            )
        except Exception as e:
            message = f"Failed to fetch metrics for host {rrd_file}: {str(e)}"
            logger.error(message)
            return { "error": message }

    def destroy_rrd_file(self, host_id: str) -> None:
        """
        Safely remove the RRD file for a host.
        
        Args:
            host_id: The UUID of the host whose RRD file should be removed
            
        Raises:
            FileNotFoundError: If the RRD file doesn't exist
            PermissionError: If there are permission issues deleting the file
            Exception: For any other unexpected errors
        """
        rrd_path = self.get_rrd_path(host_id)
        
        if not rrd_path.exists():
            logger.warning(f"RRD file not found for host {host_id}")
            return
        
        try:
            rrd_path.unlink()  # Using pathlib's unlink() for safe file deletion
            logger.info(f"Successfully removed RRD file for host {host_id}")
        except PermissionError as e:
            logger.error(f"Permission denied when removing RRD file for host {host_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to remove RRD file for host {host_id}: {str(e)}")
            raise