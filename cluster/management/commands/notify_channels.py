from django.core.management.base import BaseCommand
import channels.layers
#from django.db import connection
import psycopg
import json
from asgiref.sync import async_to_sync

class Command(BaseCommand):
    help = "Start a LISTENer to notify channels about spots"

    def handle(self, *args, **options):

        channel_layer = channels.layers.get_channel_layer()

        connection = psycopg.connect("service=rrdxa application_name=notify_channels", autocommit=True)
        connection.execute("LISTEN spot")

        try:
            for notify in connection.notifies():
                m = json.loads(notify.payload)
                self.stdout.write(notify.payload)
                channel = m['channel']
                spot = m['spot']

                async_to_sync(channel_layer.group_send)(channel, {'type': 'spot_message', "spot": spot})
        except (BrokenPipeError, KeyboardInterrupt):
            pass
