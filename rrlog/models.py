from django.db import models

from .fields import TimeText


class Event(models.Model):
    event_id = models.IntegerField(primary_key=True)
    cabrillo_name = models.CharField(null=True, blank=True)
    event = models.CharField()
    start = models.DateTimeField()
    stop = models.DateTimeField()
    author = models.CharField()
    created = models.DateTimeField()
    vhf = models.BooleanField()

    def __str__(self):
        return self.event

    class Meta:
        managed = False
        db_table = "event"


class Schedule(models.Model):
    id = models.AutoField(primary_key=True)
    cabrillo_name = models.TextField()
    prefix = models.TextField()
    dateformat = models.TextField()
    day = models.IntegerField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)
    week = models.IntegerField(null=True, blank=True)
    dow = models.IntegerField(null=True, blank=True)
    start = TimeText()
    days = models.IntegerField()
    stop = TimeText()
    vhf = models.BooleanField()
    comment = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.cabrillo_name} ({self.month}/{self.week}/{self.dow})"

    class Meta:
        managed = False
        db_table = "schedule"
        ordering = ("month", "week", "day", "dow", "cabrillo_name")
