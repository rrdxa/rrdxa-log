from django.contrib import admin
from .models import Event

class EventAdmin(admin.ModelAdmin):
    list_display = ('event', 'start', 'stop', 'vhf')

admin.site.register(Event, EventAdmin)
