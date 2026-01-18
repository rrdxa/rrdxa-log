from django.db import models

class Event(models.Model):
    event_id = models.IntegerField(primary_key=True)
    cabrillo_name = models.CharField()
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
