import json

from asgiref.sync import async_to_sync
import channels.layers
from channels.generic.websocket import WebsocketConsumer
from django.db import connection

class PGConsumer(WebsocketConsumer):

    def connect(self):
        self.channel_layer = channels.layers.get_channel_layer()
        self.accept()

    # Receive message from WebSocket
    def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
        except json.decoder.JSONDecodeError:
            return

        if 'channel' in text_data_json and 'spot' in text_data_json:
            async_to_sync(self.channel_layer.group_send)(text_data_json['channel'],
                {'type': 'spot_message', "spot": text_data_json['spot']})

class SpotConsumer(WebsocketConsumer):

    def connect(self):
        self.spot_channel = "cluster"

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.spot_channel, self.channel_name)

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.spot_channel, self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
        except json.decoder.JSONDecodeError:
            return

        if 'channel' in text_data_json:
            async_to_sync(self.channel_layer.group_discard)(
                self.spot_channel, self.channel_name)
            self.spot_channel = text_data_json["channel"]
            print(f"switching to {self.spot_channel}")
            async_to_sync(self.channel_layer.group_add)(
                self.spot_channel, self.channel_name)

        if 'load' in text_data_json:
            with connection.cursor() as cursor:
                limit = int(text_data_json['load'])
                cursor.execute("select jsonb_agg(data order by spot_time) from (select spot_time, jsonb_set_lax(data, '{spots}', jsonb_build_array(data['spots'][0])) as data from bandmap join rule on data @@ jsfilter where channel = %s order by spot_time desc limit %s)",
                               [self.spot_channel, limit])
                spots = cursor.fetchone()[0] or '[]'
                self.send(text_data=json.dumps({"spots": json.loads(spots)}))

    # Receive spot message from PostgreSQL
    def spot_message(self, event):
        spot = event["spot"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"spot": spot}))
