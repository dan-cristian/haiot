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
    subscribe()

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning("Unexpected disconnection from mqtt")
    logging.warning("Disconnected from mqtt")
    client_connected = False

def subscribe():
    global topic
    logging.info('Subscribing to mqtt topic{}'.format(topic))
    mqtt_client.on_subscribe = receiver.on_subscribe
    mqtt_client.username_pw_set(constant.HOST_NAME)
    mqtt_client.user_data_set(constant.HOST_NAME + " userdata")
    mqtt_client.will_set(constant.HOST_NAME + " DIE")
    mqtt_client.subscribe(topic=topic, qos=0)

def unload():
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    global mqtt_client, topic
    mqtt_client.unsubscribe(topic)
    mqtt_client.disconnect()
    mqtt_client.loop_stop()

def init():
    host_list=[
        [model_helper.get_param(constant.P_MQTT_HOST_1), int(model_helper.get_param(constant.P_MQTT_PORT_1))],
        [model_helper.get_param(constant.P_MQTT_HOST_2), int(model_helper.get_param(constant.P_MQTT_PORT_2))]
        ]
    global topic
    topic=str(model_helper.get_param(constant.P_MQTT_TOPIC))
    global mqtt_client
    mqtt_client = mqtt.Client()
    global client_connected
    global initialised
    for host_port in host_list:
        host = host_port[0]
        port = host_port[1]
        logging.info('MQTT publisher module initialising, host={} port={}'.format(host, port))
        client_connected=False
        retry_count=0
        while (not client_connected) and (retry_count < constant.ERROR_CONNECT_MAX_RETRY_COUNT):
            try:
                mqtt_client.on_connect = on_connect
                mqtt_client.connect(host=host,port=port, keepalive=60)
                client_connected = True
                mqtt_client.on_message = receiver.on_message
                mqtt_client.on_disconnect = on_disconnect
                mqtt_client.loop_start()
                initialised = True
            except socket.error:
                logging.error('mqtt client not connected, err {}, pause and retry'.format(sys.exc_info()[0]))
                retry_count += 1
                time.sleep(constant.ERROR_CONNECT_PAUSE_SECOND)
        if client_connected:
            break
        else:
            logging.warning('Unable to connect to mqtt server {}:{}'.format(host, port))
    if not client_connected:
        logging.critical('MQTT connection not available, all connect attempts failed')

