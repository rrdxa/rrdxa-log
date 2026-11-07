from django import forms
from django.contrib import admin

from .fields import TimeText
from .models import Event, Schedule

class EventAdmin(admin.ModelAdmin):
    list_display = ('event', 'start', 'stop', 'vhf')

admin.site.register(Event, EventAdmin)

class ScheduleAdmin(admin.ModelAdmin):
    # The admin maps every TextField to a textarea; a time value wants one line.
    formfield_overrides = {TimeText: {'widget': forms.TextInput}}
    list_display = ('cabrillo_name', 'prefix', 'month', 'week', 'dow', 'start', 'days', 'stop', 'vhf', 'comment')
    list_filter = ('month', 'vhf')
    search_fields = ('cabrillo_name', 'prefix', 'comment')
    ordering = ('month', 'week', 'day', 'dow', 'cabrillo_name')

admin.site.register(Schedule, ScheduleAdmin)
