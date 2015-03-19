__author__ = 'dcristian'

import paho.mqtt.client as mqtt
import json
import socket
import time
from collections import namedtuple
from main.admin import thread_pool
import logging
from main.admin import model_helper
from common import constant

mqtt_client = None
client_connected = False

#http://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object
def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
def json2obj(data): return json.loads(data, object_hook=_json_object_hook)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logging.info("Connected to mqtt with result code " + str(rc))
    client_connected = True

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning("Unexpected disconnection from mqtt")
    logging.warning("Disconnected from mqtt")
    client_connected = False

def unload():
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    global mqtt_client
    mqtt_client.loop_stop()

def init():
    logging.info('MQTT publisher module initialising')
    global mqtt_client
    mqtt_client = mqtt.Client()
    global client_connected
    client_connected=False
    retry_count=0
    while (not client_connected) and (retry_count < constant.ERROR_CONNECT_MAX_RETRY_COUNT):
        try:
            mqtt_client.on_connect = on_connect
            mqtt_client.connect(model_helper.get_param(constant.PARAM_MQTT_HOST),
                model_helper.get_param(constant.PARAM_MQTT_PORT), 60)
            client_connected = True
            #client.on_message = on_message
            mqtt_client.on_disconnect = on_disconnect
            #client.on_subscribe = on_subscribe
            mqtt_client.username_pw_set(socket.gethostname())
            mqtt_client.user_data_set(socket.gethostname() + " userdata")
            mqtt_client.will_set(socket.gethostname() + " DIE")
            mqtt_client.loop_start()
        except socket.error:
            logging.error('mqtt client not connected, pause and retry')
            retry_count += 1
            time.sleep(constant.ERROR_CONNECT_PAUSE_SECOND)
