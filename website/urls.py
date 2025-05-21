from django.urls import path
from . import views

urlpatterns = [
    path("", views.summary, name="summary"),
    path("summary", views.summary, name="summary"),
    path("summary/host_info", views.summary_host_info, name="summary_host_info"),

    # Monitored Hosts
    path("monitored_hosts", views.monitored_hosts, name="monitored_hosts"),
    path("monitored_hosts/add", views.monitored_hosts_add, name="monitored_hosts_add"),
    path("monitored_hosts/settings", views.monitored_hosts_settings, name="monitored_hosts_settings"),
    path("monitored_hosts/metrics", views.monitored_hosts_metrics, name="monitored_hosts_metrics"),
    path("monitored_hosts/import", views.monitored_hosts_import, name="monitored_hosts_import"),

    # Unmonitored Hosts
    path("unmonitored_hosts", views.unmonitored_hosts, name="unmonitored_hosts"),
    path("unmonitored_hosts/remonitor", views.unmonitored_hosts_remonitor, name="unmonitored_hosts_remonitor"),
    path("unmonitored_hosts/delete", views.unmonitored_hosts_delete, name="unmonitored_hosts_delete"),

    # Log Monitor
    path("log_monitor", views.log_monitor, name="log_monitor"),
    path("log_monitor/fetch", views.log_monitor_fetch, name="log_monitor_fetch"),

    # Admin Tools
    path("admin_tools", views.admin_tools, name="admin_tools"),
    path("admin_tools/monitor_status", views.admin_tools_monitor_status, name="admin_tools_monitor_status"),
    path("admin_tools/monitor_control", views.admin_tools_monitor_control, name="admin_tools_monitor_control"),
    path("admin_tools/system_info", views.admin_tools_system_info, name="admin_tools_system_info"),
    path("admin_tools/global_settings", views.admin_tools_global_settings, name="admin_tools_global_settings"),
]