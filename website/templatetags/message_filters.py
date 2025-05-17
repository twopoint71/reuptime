# templatetags/message_filters.py
from django import template

register = template.Library()

@register.filter(name='bootstrap_alert_class')
def bootstrap_alert_class(tag):
    return {
        'error': 'danger',
        'debug': 'secondary',
    }.get(tag, tag)
