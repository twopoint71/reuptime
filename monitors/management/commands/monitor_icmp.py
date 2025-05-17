from django.core.management.base import BaseCommand
from monitors.models import MonitorStatus
from monitors.icmp import run_monitor
from datetime import datetime
import os
import signal
import psutil
import logging
import sys
import subprocess

logger = logging.getLogger('monitors')

class Command(BaseCommand):
    help = 'Control the ICMP monitor daemon (start/stop/restart)'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['start', 'stop', 'restart', 'status'],
            help='Action to perform on the ICMP monitor'
        )

    def get_monitor_status(self):
        """Get or create monitor status record"""
        status, created = MonitorStatus.objects.get_or_create(
            monitor_type='icmp',
            defaults={
                'status': 'stopped',
                'pid': None
            }
        )
        return status

    def is_process_running(self, pid):
        """Check if a process is running"""
        try:
            return psutil.pid_exists(pid) and psutil.Process(pid).name().startswith('python')
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def start_monitor(self):
        """Start the ICMP monitor daemon"""
        status = self.get_monitor_status()

        # Check if already running
        if status.status == 'running' and status.pid and self.is_process_running(status.pid):
            self.stdout.write(self.style.WARNING('ICMP monitor is already running'))
            return

        # Start the daemon
        try:
            # Use subprocess.Popen to start the daemon
            process = subprocess.Popen(
                [sys.executable, 'manage.py', 'shell', '-c', 'from monitors.icmp import run_monitor; run_monitor()'],
                stdout=subprocess.DEVNULL,  # Redirect stdout to /dev/null
                stderr=subprocess.DEVNULL,  # Redirect stderr to /dev/null
                preexec_fn=os.setpgrp  # Create new process group
            )

            # Update status
            status.status = 'running'
            status.pid = process.pid
            status.save()

            self.stdout.write(self.style.SUCCESS(f'ICMP monitor started with PID {process.pid}'))
            logger.info(f'ICMP monitor started with PID {process.pid}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to start ICMP monitor: {str(e)}'))
            logger.error(f'Failed to start ICMP monitor: {str(e)}')

    def stop_monitor(self):
        """Stop the ICMP monitor daemon"""
        status = self.get_monitor_status()

        if status.status != 'running' or not status.pid:
            self.stdout.write(self.style.WARNING('ICMP monitor is not running'))
            return

        try:
            # Try to terminate the process
            if self.is_process_running(status.pid):
                os.kill(status.pid, signal.SIGTERM)
                # Wait for process to terminate
                try:
                    os.waitpid(status.pid, 0)
                except ChildProcessError:
                    pass

            # Update status
            status.status = 'stopped'
            status.pid = None
            status.save()

            self.stdout.write(self.style.SUCCESS('ICMP monitor stopped'))
            logger.info('ICMP monitor stopped')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to stop ICMP monitor: {str(e)}'))
            logger.error(f'Failed to stop ICMP monitor: {str(e)}')

    def restart_monitor(self):
        """Restart the ICMP monitor daemon"""
        self.stop_monitor()
        self.start_monitor()

    def show_status(self):
        """Show the current status of the ICMP monitor"""
        status = self.get_monitor_status()

        if status.status == 'running' and status.pid:
            if self.is_process_running(status.pid):
                self.stdout.write(self.style.SUCCESS(
                    f'ICMP monitor is running (PID: {status.pid}, Last Activity: {status.last_active})'
                ))
            else:
                # Process is not running but status says it is
                status.status = 'stopped'
                status.pid = None
                status.last_active = datetime.utcnow()
                status.save()
                self.stdout.write(self.style.WARNING('ICMP monitor is not running (stale status)'))
        else:
            self.stdout.write(self.style.WARNING(
                f'ICMP monitor is stopped (Last Activity: {status.last_active})'
            ))

    def handle(self, *args, **options):
        action = options['action']

        if action == 'start':
            self.start_monitor()
        elif action == 'stop':
            self.stop_monitor()
        elif action == 'restart':
            self.restart_monitor()
        elif action == 'status':
            self.show_status()