# templatetags/json_extras.py
import json
from django import template
from django.core import serializers

register = template.Library()

@register.filter
def model_to_json(obj):
    serialized = serializers.serialize('json', [obj])
    data = json.loads(serialized)[0]['fields']
    return json.dumps(data)
