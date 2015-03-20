__author__ = 'dcristian'

import paho.mqtt.client as mqtt
import socket
import time
import sys

from main.admin import thread_pool
import logging
from main.admin import model_helper
from common import constant
import receiver
import sender

initialised=False
mqtt_client = None
client_connected = False
topic='no_topic_defined'

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
    host=model_helper.get_param(constant.PARAM_MQTT_HOST)
    port=int(model_helper.get_param(constant.PARAM_MQTT_PORT))
    global topic
    topic=str(model_helper.get_param(constant.PARAM_MQTT_TOPIC))
    logging.info('MQTT publisher module initialising, host={} port={}'.format(host, port))
    global mqtt_client
    mqtt_client = mqtt.Client()
    global client_connected
    client_connected=False
    retry_count=0
    while (not client_connected) and (retry_count < constant.ERROR_CONNECT_MAX_RETRY_COUNT):
        try:
            mqtt_client.on_connect = on_connect
            mqtt_client.connect(host=host,port=port, keepalive=60)
            client_connected = True
            mqtt_client.on_message = receiver.on_message
            mqtt_client.on_disconnect = on_disconnect
            mqtt_client.on_subscribe = receiver.on_subscribe
            mqtt_client.username_pw_set(socket.gethostname())
            mqtt_client.user_data_set(socket.gethostname() + " userdata")
            mqtt_client.will_set(socket.gethostname() + " DIE")

            mqtt_client.subscribe(topic=topic, qos=0)
            
            mqtt_client.loop_start()
        except socket.error:
            logging.error('mqtt client not connected, err {}, pause and retry'.format(sys.exc_info()[0]))
            retry_count += 1
            time.sleep(constant.ERROR_CONNECT_PAUSE_SECOND)
    global initialised
    initialised = True
