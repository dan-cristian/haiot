__author__ = 'dcristian'

import socket
import time
import sys

import paho.mqtt.client as mqtt

from main.admin import thread_pool
from main import logger
from main.admin import model_helper
from common import constant
import receiver
import sender


initialised=False
mqtt_client = None
client_connected = False
topic='no_topic_defined'
client_connecting = False

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger.info("Connected to mqtt with result code " + str(rc))
    global client_connected
    client_connected = True
    subscribe()

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected disconnection from mqtt")
    logger.warning("Disconnected from mqtt")
    global client_connected
    client_connected = False

def subscribe():
    global topic
    logger.info('Subscribing to mqtt topic={}'.format(topic))
    mqtt_client.on_subscribe = receiver.on_subscribe
    mqtt_client.username_pw_set(constant.HOST_NAME)
    mqtt_client.user_data_set(constant.HOST_NAME + " userdata")
    mqtt_client.will_set(constant.HOST_NAME + " DIE")
    mqtt_client.subscribe(topic=topic, qos=0)

def unload():
    global mqtt_client, topic
    mqtt_client.unsubscribe(topic)
    try:
        mqtt_client.loop_stop()
    except Exception, ex:
        logger.warning('Unable to stop mqtt loop, err {}'.format(ex))
    mqtt_client.disconnect()

def init():
    global client_connecting
    if client_connecting:
        logger.warning('Mqtt client already in connection process, skipping attempt to connect until done')
        return

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
        client_connecting = True
        host = host_port[0]
        port = host_port[1]
        logger.info('MQTT publisher module initialising, host={} port={}'.format(host, port))
        client_connected=False
        retry_count=0
        while (not client_connected) and (retry_count < constant.ERROR_CONNECT_MAX_RETRY_COUNT):
            try:
                mqtt_client.on_connect = on_connect
                mqtt_client.connect(host=host,port=port, keepalive=60)
                client_connected = True
                mqtt_client.on_message = receiver.on_message
                mqtt_client.on_disconnect = on_disconnect
                thread_pool.add_callable(receiver.thread_run, run_interval_second=10)
                mqtt_client.loop_start()
                initialised = True
                client_connecting = False
            except socket.error:
                logging.error('mqtt client not connected, err {}, pause and retry'.format(sys.exc_info()[0]))
                retry_count += 1
                time.sleep(constant.ERROR_CONNECT_PAUSE_SECOND)
            finally:
                client_connecting = False
        if client_connected:
            break
        else:
            logger.warning('Unable to connect to mqtt server {}:{}'.format(host, port))
    if not client_connected:
        logger.critical('MQTT connection not available, all connect attempts failed')

