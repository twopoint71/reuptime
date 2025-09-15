from typing import Dict, Any
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest
from django.contrib import messages
from rrd.services import RRDService

from website.services import (
    HostService, MonitorService, LogService, 
    SystemService, SettingsService
)

def summary(request: HttpRequest) -> Any:
    host_count = HostService.get_host_count()
    return render(request, "summary.html", {"host_count": host_count})


def summary_host_info(request: HttpRequest) -> JsonResponse:
    return JsonResponse({
        "monitored_active_count": HostService.get_monitored_active_count(),
        "monitored_inactive_count": HostService.get_monitored_inactive_count(),
        "monitored_has_allotment_count": HostService.get_monitored_has_allotment_count(),
        "monitored_has_no_allotment_count": HostService.get_monitored_has_no_allotment_count()
    })

def monitored_hosts(request: HttpRequest) -> Any:
    host_list = HostService.get_monitored_hosts()
    return render(request, "monitored_hosts.html", {"host_list": host_list})

def monitored_hosts_settings(request: HttpRequest) -> Any:
    try:
        action = request.POST.get("action")
        uuid = request.POST.get("uuid")
        if action == "unmonitorHost":
            host = HostService.update_host_monitoring_status(uuid, False)
            messages.success(request, f"Host {host.host_name} unmonitored successfully!")
        elif action == "updateHost":
            host_data = {
                "uuid": uuid,
                "downtime_allotment": request.POST.get("downtime_allotment"),
                "monitor_type": request.POST.get("monitor_type"),
                "monitor_params": request.POST.get("monitor_params"),
            }
            host = HostService.update_host_settings(uuid, host_data)
            messages.success(request, f"Host {host.host_name} updated successfully!")
    except Exception as e:
        messages.error(request, f"Failed to {action} host: {str(e)}")
    return redirect('monitored_hosts')

def monitored_hosts_add(request: HttpRequest) -> Any:
    try:
        host_data = {
            "account_label": request.POST.get("account_label"),
            "account_id": request.POST.get("account_id"),
            "region": request.POST.get("region"),
            "host_id": request.POST.get("host_id"),
            "host_ip_address": request.POST.get("host_ip_address"),
            "host_name": request.POST.get("host_name"),
            "downtime_allotment": request.POST.get("downtime_allotment"),
            "monitor_type": request.POST.get("monitor_type"),
            "monitor_params": request.POST.get("monitor_params"),
        }
        
        host = HostService.create_host(host_data)
        messages.success(request, f"Host {host.host_name} added successfully!")
    except Exception as e:
        messages.error(request, f"Failed to add host: {str(e)}")
    return redirect('monitored_hosts')

def monitored_hosts_import(request: HttpRequest) -> Any:
    try:
        if 'csv_file' not in request.FILES:
            messages.error(request, "No CSV file uploaded")
            return redirect('monitored_hosts')

        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "File must be a CSV")
            return redirect('monitored_hosts')

        # Read and decode CSV content
        file_data = csv_file.read().decode('utf-8')
        lines = file_data.split('\n')
        
        # Skip header row and empty lines
        data_lines = [line for line in lines[1:] if line.strip()]
        
        success_count = 0
        duplicate_count = 0
        error_count = 0
        
        for line in data_lines:
            try:
                # Split CSV line and remove quotes
                fields = [field.strip('"') for field in line.split(',')]
                
                if len(fields) < 6:  # Minimum required fields
                    continue
                    
                host_data = {
                    "account_label": fields[0],
                    "account_id": fields[1],
                    "region": fields[2], 
                    "host_id": fields[3],
                    "host_ip_address": fields[4],
                    "host_name": fields[5],
                    "downtime_allotment": fields[6] if len(fields) > 6 and fields[6] else "",
                    "monitor_type": fields[7] if len(fields) > 7 and fields[7] else "icmp",
                    "monitor_params": fields[8] if len(fields) > 8 and fields[8] else ""
                }
                
                host = HostService.create_host(host_data)
                if host == None:
                    duplicate_count += 1
                else:
                    success_count += 1
                
            except Exception as e:
                error_count += 1
                continue

        if success_count > 0:
            messages.success(request, f"Successfully imported {success_count} hosts")
        elif duplicate_count > 0:
            messages.warning(request, f"Skipped {duplicate_count} duplicate hosts")
        elif error_count > 0:
            messages.warning(request, f"Failed to import {error_count} hosts")
            
    except Exception as e:
        messages.error(request, f"Error processing CSV file: {str(e)}")
        
    return redirect('monitored_hosts')

def monitored_hosts_metrics(request: HttpRequest) -> JsonResponse:
    host_uuid = request.GET.get("host_uuid")
    time_range_resolution_code = int(request.GET.get("time_range_resolution_code", 1))
    rrd = RRDService()
    rrd_data = rrd.get_metrics(host_uuid, time_range_resolution_code)
    
    return JsonResponse({
        "time_range_resolution_code": time_range_resolution_code,
        "rrd_file": host_uuid,
        "rrd_data": rrd_data,
    }, safe=False)
        
def unmonitored_hosts(request: HttpRequest) -> Any:
    host_list = HostService.get_unmonitored_hosts()
    return render(request, "unmonitored_hosts.html", {"host_list": host_list})

def unmonitored_hosts_remonitor(request: HttpRequest) -> Any:
    try:
        host_uuid = request.GET.get("host_uuid")
        host = HostService.update_host_monitoring_status(host_uuid, True)
        messages.success(request, f"Host {host.host_name} remonitored successfully!")
    except Exception as e:
        messages.error(request, f"Failed to remonitor host: {str(e)}")
    return redirect('unmonitored_hosts')

def unmonitored_hosts_delete(request: HttpRequest) -> Any:
    try:
        host_uuid = request.GET.get("host_uuid")
        host = HostService.delete_host(host_uuid)
        rrd = RRDService()
        rrd.destroy_rrd_file(host_uuid)
        messages.success(request, f"Host {host.host_name} deleted successfully!")
    except Exception as e:
        messages.error(request, f"Failed to delete host: {str(e)}")
    return redirect('unmonitored_hosts')

def log_monitor(request: HttpRequest) -> Any:
    return render(request, "log_monitor.html")

def log_monitor_fetch(request: HttpRequest) -> JsonResponse:
    try:
        log_type = request.GET.get("log_type", "monitors")
        log_tail = int(request.GET.get("log_tail", 50))
        from datetime import datetime
        server_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_content = LogService.get_log_content(log_type, log_tail)
        return JsonResponse({"log_content": log_content, "server_timestamp": server_timestamp}, safe=False)
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "log_content": f"Error reading log file: {str(e)}"
        })

def admin_tools(request: HttpRequest) -> Any:
    context = {
        'default_downtime_allotment': SettingsService.get_default_downtime_allotment(),
        'auto_start_monitors': SettingsService.get_auto_start_monitors(),
    }
    return render(request, 'admin_tools.html', context)

def admin_tools_monitor_status(request: HttpRequest) -> JsonResponse:
    try:
        monitor_type = request.GET.get('monitor_type', 'icmp')
        status_data = MonitorService.get_monitor_status(monitor_type)
        return JsonResponse(status_data, safe=False)
    except MonitorStatus.DoesNotExist:
        return JsonResponse({
            'status': 'unknown',
            'pid': None,
            'message': f'No status found for {monitor_type} monitor',
            'last_update': None
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'pid': None,
            'message': str(e),
            'last_update': None
        })

def admin_tools_monitor_control(request: HttpRequest) -> Any:
    try:
        monitor_type = request.GET.get('monitor_type')
        action = request.GET.get('action')
        
        MonitorService.control_monitor(monitor_type, action)
        messages.success(request, f"Monitor {monitor_type} action {action} completed successfully!")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Failed to action {action} monitor {monitor_type}: {str(e)}")
    return redirect('admin_tools')

def admin_tools_system_info(request: HttpRequest) -> JsonResponse:
    try:
        data = SystemService.get_system_info()
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def admin_tools_global_settings(request: HttpRequest) -> Any:
    try:
        downtime_allotment = request.POST.get("default_downtime_allotment")
        SettingsService.update_default_downtime_allotment(downtime_allotment)
        
        auto_start = request.POST.get("auto_start_monitors") == "on"
        SettingsService.update_auto_start_monitors(auto_start)
        
        messages.success(request, "Global settings updated successfully!")
    except Exception as e:
        messages.error(request, f"Failed to update global settings: {str(e)}")
    return redirect('admin_tools')