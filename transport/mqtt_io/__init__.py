import time
import socket
import threading
import json
from main.logger_helper import L
from common import Constant, utils
import common

from common import fix_module
while True:
    try:
        from pydispatch import dispatcher
        import paho.mqtt.client as mqtt
        import prctl
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


class P:
    topic = 'no_topic_defined'
    topic_main = 'no_main_topic_defined'
    mqtt_client = None
    client_connected = False
    is_client_connecting = False
    mqtt_msg_count_per_minute = 0
    last_connect_attempt = utils.get_base_location_now_date()
    mqtt_mosquitto_exists = False
    mqtt_paho_exists = False
    last_rec = utils.get_base_location_now_date()
    last_minute = 0
    received_mqtt_list = []
    message_callbacks = {}

    def __init__(self):
        pass


try:
    if not P.mqtt_mosquitto_exists:
        import paho.mqtt.client as mqtt
        P.mqtt_paho_exists = True
except Exception:
    P.mqtt_paho_exists = False


__author__ = 'dcristian'


def add_message_callback(topic, callback):
    P.message_callbacks[topic] = callback
    P.mqtt_client.message_callback_add(topic, callback)


# The callback for when the client receives a CONNACK response from the server.
def on_connect_paho(client, userdata, flags, rc):
    L.l.info("Connected to mqtt paho with result code " + str(rc))
    # P.client_connected = True
    subscribe()


def on_connect_mosquitto(mosq, userdata, rc):
    L.l.info("Connected to mqtt mosquitto with result code " + str(rc))
    subscribe()


def on_disconnect(client, userdata, rc):
    if rc != 0:
        L.l.warning("Unexpected disconnection from mqtt")
    else:
        L.l.info("Expected disconnect from mqtt")
    P.mqtt_client.loop_stop()
    P.client_connected = False


def on_subscribe(client, userdata, mid, granted_qos):
    P.client_connected = True
    L.l.info("Mqtt subscribed")
    for topic in P.message_callbacks:
        P.mqtt_client.message_callback_add(topic, P.message_callbacks[topic])


# def on_subscribe(client, userdata, mid, granted_qos):
#    Log.logger.info('Subscribed as user {} mid {} qos {}'.format(str(userdata), str(mid), str(granted_qos)))


def on_unsubscribe(client, userdata, mid):
    # P.client_connected = False
    pass


def subscribe():
    L.l.info('Subscribing to mqtt topic={}'.format(P.topic))
    P.mqtt_client.username_pw_set(Constant.HOST_NAME)
    P.mqtt_client.user_data_set(Constant.HOST_NAME + " userdata")
    P.mqtt_client.will_set(Constant.HOST_NAME + " DIE")
    # P.mqtt_client.subscribe(topic=P.topic, qos=0)
    # subscribe to all topics to catch all
    P.mqtt_client.subscribe(topic="#", qos=0)


def payload2json(payload):
    # locate json string and clean escape chars
    res = str(payload).replace('\\', '')
    start = res.find('{')
    end = res.rfind('}')
    res = res[start:end + 1]
    return res


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    if threading.current_thread().name != 'mqtt_loop':
        prctl.set_name("mqtt_loop")
        threading.current_thread().name = "mqtt_loop"
    start = utils.get_base_location_now_date()
    json = msg
    try:
        if utils.get_base_location_now_date().minute != P.last_minute:
            P.last_minute = utils.get_base_location_now_date().minute
            P.mqtt_msg_count_per_minute = 0
        P.mqtt_msg_count_per_minute += 1
        P.last_rec = utils.get_base_location_now_date()
        json = payload2json(msg.payload)
        # ignore messages sent by this host
        if '"source_host_": "{}"'.format(Constant.HOST_NAME) not in json \
                and '"source_host": "{}"'.format(Constant.HOST_NAME) not in json \
                and len(json) > 0:  # or Constant.HOST_NAME == 'netbook': #debug
            x = utils.json2obj(json)
            if '_sent_on' in x:
                delta = (start - utils.parse_to_date(x['_sent_on'])).total_seconds()
                # L.l.info('Mqtt age={}'.format(delta))
                if delta > 5:
                    if 'source_host' in x:
                        host = x['source_host']
                    else:
                        host = 'N/A'
                    L.l.info('Mqtt delta {} source_host='.format(delta, host))
            x['is_event_external'] = True
            P.received_mqtt_list.append(x)
        else:
            pass
    except Exception as ex:
        L.l.warning('Unknown attribute error in msg {} err {}'.format(json, ex))
    prctl.set_name("idle_mqtt_loop")
    threading.current_thread().name = "idle_mqtt_loop"


def unload():
    P.mqtt_client.unsubscribe(P.topic)
    try:
        P.mqtt_client.loop_stop()
    except Exception as ex:
        L.l.warning('Unable to stop mqtt loop, err {}'.format(ex))
    P.mqtt_client.disconnect()


def init():
    if P.mqtt_mosquitto_exists:
        L.l.info("INIT, Using mosquitto as mqtt client")
    elif P.mqtt_paho_exists:
        L.l.info("INIT, Using paho as mqtt client")
    else:
        L.l.critical("No mqtt client enabled via import")
        raise Exception("No mqtt client enabled via import")

    # not a good ideea to set a timeout as it will crash pigpio_gpio callback
    # socket.setdefaulttimeout(10)
    try:
        if P.is_client_connecting is True:
            L.l.warning('Mqtt client already in connection process, skipping attempt to connect until done')
            return False
        P.is_client_connecting = True
        host_list = [
            [common.get_json_param(common.Constant.P_MQTT_HOST_1), int(common.get_json_param(Constant.P_MQTT_PORT_1))],
            [common.get_json_param(Constant.P_MQTT_HOST_2), int(common.get_json_param(Constant.P_MQTT_PORT_2))]]
        config_file = common.get_json_param(Constant.P_ALL_CREDENTIAL_FILE)
        with open(config_file, 'r') as f:
            config = json.load(f)
            user = config['mqtt_username']
            passwd = config['mqtt_password']
        P.topic = str(common.get_json_param(Constant.P_MQTT_TOPIC))
        P.topic_main = str(common.get_json_param(Constant.P_MQTT_TOPIC_MAIN))
        if P.mqtt_paho_exists:
            P.mqtt_client = mqtt.Client(client_id=Constant.HOST_NAME)
        elif P.mqtt_mosquitto_exists:
            P.mqtt_client = mqtt.Mosquitto(client_id=Constant.HOST_NAME)
        else:
            L.l.error("Unable to create the Mqtt client")

        for host_port in host_list:
            host = host_port[0]
            port = host_port[1]
            L.l.info('MQTT publisher module initialising, host={} port={}'.format(host, port))
            retry_count = 0
            while (not P.client_connected) and (retry_count < Constant.ERROR_CONNECT_MAX_RETRY_COUNT):
                try:
                    if P.mqtt_mosquitto_exists:
                        P.mqtt_client.on_connect = on_connect_mosquitto
                    if P.mqtt_paho_exists:
                        P.mqtt_client.on_connect = on_connect_paho
                    P.mqtt_client.on_subscribe = on_subscribe
                    P.mqtt_client.on_unsubscribe = on_unsubscribe
                    P.mqtt_client.username_pw_set(user, passwd)
                    P.mqtt_client.max_inflight_messages_set(100)
                    P.mqtt_client.max_queued_messages_set(0)
                    P.mqtt_client.connect(host=host, port=port, keepalive=60)
                    P.mqtt_client.loop_start()
                    seconds_lapsed = 0
                    while not P.client_connected and seconds_lapsed < 10:
                        time.sleep(1)
                        seconds_lapsed += 1
                        L.l.info('Waiting for mqtt connect {}'.format(seconds_lapsed))
                    if P.client_connected:
                        P.mqtt_client.message_callback_add(P.topic_main, on_message)
                        P.mqtt_client.on_disconnect = on_disconnect
                        # thread_pool.add_interval_callable(thread_run, run_interval_second=10)
                        P.initialised = True
                    else:
                        L.l.warning('Timeout connecting to mqtt')
                        retry_count += 1
                except socket.error as ex:
                    L.l.error('mqtt client not connected, err {}, pause and retry {}'.format(ex, retry_count))
                    retry_count += 1
                    time.sleep(Constant.ERROR_CONNECT_PAUSE_SECOND)
                finally:
                    P.last_connect_attempt = utils.get_base_location_now_date()
            if P.client_connected:
                L.l.info('Noticed mqtt connected, init')
                break
            else:
                L.l.warning('Unable to connect to mqtt server {}:{}'.format(host, port))
        if not P.client_connected:
            L.l.critical('MQTT connection not available, all connect attempts failed')
    except Exception as ex:
        L.l.error('Exception on mqtt init, err={}'.format(ex))

    finally:
        P.is_client_connecting = False


def _send_message(txt, topic=None):
    try:
        if topic is None:
            topic = P.topic_main
        # Log.logger.debug('Sending message at {} [{}] '.format(utils.get_base_location_now_date(), txt))
        if P.client_connected:
            P.mqtt_client.publish(topic=topic, payload="{}".format(txt), qos=1, retain=True)
            return True
        else:
            # Log.logger.debug('MQTT client not connected, retrying connect, message to be discarded: {}'.format(txt))
            return False
    except Exception as ex:
        L.l.error('Error sending mqtt message, topic={}, payload={}, err={}'.format(topic, txt, ex), exc_info=True)
        return False
