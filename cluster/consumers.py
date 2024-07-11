import json
import re

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

        elif 'channel' in text_data_json and 'rule' in text_data_json:
            async_to_sync(self.channel_layer.group_send)(text_data_json['channel'],
                {'type': 'rule_message', "rule": text_data_json['rule']})

class SpotConsumer(WebsocketConsumer):

    def connect(self):
        self.spot_channel = None
        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        if self.spot_channel:
            async_to_sync(self.channel_layer.group_discard)(
                self.spot_channel, self.channel_name)

    # Receive message from WebSocket
    def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
        except json.decoder.JSONDecodeError:
            return

        if 'channel' in text_data_json:
            new_channel = text_data_json['channel']
            if not re.match(r'[\w.-]{1,99}$', new_channel): # django-channels namespace
                return

            with connection.cursor() as cursor:
                cursor.execute("select timeout::text, rule from rule where channel = %s", [new_channel])
                data = cursor.fetchone()
                if data is None:
                    self.send(text_data=json.dumps({"message": f"Channel {new_channel} does not exist"}))
                    return
                else:
                    timeout = data[0]
                    rule = json.loads(data[1])
                    self.send(text_data=json.dumps({"rule": {"timeout": timeout, "rule": rule}}))

            if self.spot_channel:
                async_to_sync(self.channel_layer.group_discard)(
                    self.spot_channel, self.channel_name)
            self.spot_channel = new_channel
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

        if 'delete_rule' in text_data_json:
            with connection.cursor() as cursor:
                path = text_data_json['delete_rule']
                cursor.execute("select rrdxa.rule_delete_entry(%s, %s)", [self.spot_channel, f"{{{path}}}"])

        if 'add_rule' in text_data_json and 'val' in text_data_json:
            with connection.cursor() as cursor:
                path = text_data_json['add_rule']
                val = text_data_json['val']
                cursor.execute("select rrdxa.rule_add_entry(%s, %s, %s)", [self.spot_channel, f"{{{path}}}", val])

    # Receive spot message from PostgreSQL
    def spot_message(self, event):
        spot = event["spot"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"spot": spot}))

    def rule_message(self, event):
        rule = event["rule"]
        self.send(text_data=json.dumps({"rule": rule}))
