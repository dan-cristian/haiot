__author__ = 'dcristian'

import socket
import time
import sys
from main.admin import thread_pool
from main import logger
from main.admin import model_helper
from common import constant
import receiver
import sender
import socket

mqtt_mosquitto_exists = False
mqtt_paho_exists = False

try:
    import mosquitto as mqtt
    mqtt_mosquitto_exists = True
except Exception:
    mqtt_mosquitto_exists = False

try:
    if not mqtt_mosquitto_exists:
        import paho.mqtt.client as mqtt
        mqtt_paho_exists = True
except Exception:
    mqtt_paho_exists = False


initialised=False
mqtt_client = None
client_connected = False
topic='no_topic_defined'
client_connecting = False
mqtt_msg_count_per_minute = 0

# The callback for when the client receives a CONNACK response from the server.
def on_connect_paho(client, userdata, flags, rc):
    logger.info("Connected to mqtt paho with result code " + str(rc))
    global client_connected
    client_connected = True
    subscribe()

def on_connect_mosquitto(mosq, userdata, rc):
    logger.info("Connected to mqtt mosquitto with result code " + str(rc))
    subscribe()

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected disconnection from mqtt")
    logger.warning("Disconnected from mqtt")
    global client_connected
    client_connected = False

def on_subscribe(client, userdata, mid, granted_qos):
    global client_connected
    client_connected = True
    print 'MQTT subscribed'

#def on_subscribe(client, userdata, mid, granted_qos):
#    logger.info('Subscribed as user {} mid {} qos {}'.format(str(userdata), str(mid), str(granted_qos)))

def on_unsubscribe(client, userdata, mid):
    global client_connected
    client_connected = False

def subscribe():
    global topic
    logger.info('Subscribing to mqtt topic={}'.format(topic))
    mqtt_client.username_pw_set(constant.HOST_NAME)
    mqtt_client.user_data_set(constant.HOST_NAME + " userdata")
    mqtt_client.will_set(constant.HOST_NAME + " DIE")
    mqtt_client.subscribe(topic=topic, qos=0)

def unload():
    global mqtt_client, topic, mqtt_paho_exists, mqtt_mosquitto_exists
    mqtt_client.unsubscribe(topic)
    try:
        mqtt_client.loop_stop()
    except Exception, ex:
        logger.warning('Unable to stop mqtt loop, err {}'.format(ex))
    mqtt_client.disconnect()

def init():
    if mqtt_mosquitto_exists:
        logger.info("Using mosquitto as mqtt client")
    elif mqtt_paho_exists:
        logger.info("Using paho as mqtt client")
    else:
        logger.critical("No mqtt client enabled via import")
        raise Exception("No mqtt client enabled via import")

    socket.setdefaulttimeout(10)
    try:
        global client_connecting
        if client_connecting:
            logger.warning('Mqtt client already in connection process, skipping attempt to connect until done')
            return

        host_list=[
            [model_helper.get_param(constant.P_MQTT_HOST_3), int(model_helper.get_param(constant.P_MQTT_PORT_3))],
            [model_helper.get_param(constant.P_MQTT_HOST_1), int(model_helper.get_param(constant.P_MQTT_PORT_1))],
            [model_helper.get_param(constant.P_MQTT_HOST_2), int(model_helper.get_param(constant.P_MQTT_PORT_2))]
            #[model_helper.get_param(constant.P_MQTT_HOST_3), int(model_helper.get_param(constant.P_MQTT_PORT_3))]
            ]
        global topic
        topic=str(model_helper.get_param(constant.P_MQTT_TOPIC))
        global mqtt_client
        if mqtt_paho_exists:
            mqtt_client = mqtt.Client()
        elif mqtt_mosquitto_exists:
            mqtt_client = mqtt.Mosquitto()

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
                    if mqtt_mosquitto_exists:
                        mqtt_client.on_connect = on_connect_mosquitto
                    if mqtt_paho_exists:
                        mqtt_client.on_connect = on_connect_paho
                    mqtt_client.on_subscribe = on_subscribe
                    mqtt_client.on_unsubscribe = on_unsubscribe
                    #mqtt_client.username_pw_set('user', 'pass')
                    mqtt_client.loop_start()
                    mqtt_client.connect(host=host,port=port, keepalive=60)
                    seconds_lapsed = 0
                    while not client_connected and seconds_lapsed < 10:
                        time.sleep(1)
                        seconds_lapsed += 1
                    if client_connected:
                        mqtt_client.on_message = receiver.on_message
                        mqtt_client.on_disconnect = on_disconnect
                        thread_pool.add_callable(receiver.thread_run, run_interval_second=10)
                        #mqtt_client.loop_start()
                        initialised = True
                        client_connecting = False
                    else:
                        logger.warning('Timeout connecting to mqtt')
                        retry_count += 1
                except socket.error, ex:
                    logger.error('mqtt client not connected, err {}, pause and retry {}'.format(ex, retry_count))
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
    except Exception, ex:
        logger.error('Exception on mqtt init, err={}'.format(ex))

