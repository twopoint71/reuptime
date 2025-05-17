from django.contrib import admin
from .models import Hosts, GlobalSettings

# Register your models here.
admin.site.register(Hosts)
admin.site.register(GlobalSettings)