import time
import socket
import prctl
import threading
from pydispatch import dispatcher
from main import thread_pool
from main.logger_helper import L
from main.admin import model_helper
from common import Constant, utils


class P:
    topic = 'no_topic_defined'
    topic_main = 'no_main_topic_defined'
    mqtt_client = None
    client_connected = False
    client_connecting = False
    mqtt_msg_count_per_minute = 0
    last_connect_attempt = None
    mqtt_mosquitto_exists = False
    mqtt_paho_exists = False
    last_rec = utils.get_base_location_now_date()
    last_minute = 0

    def __init__(self):
        pass


try:
    if not P.mqtt_mosquitto_exists:
        import paho.mqtt.client as mqtt
        P.mqtt_paho_exists = True
except Exception:
    P.mqtt_paho_exists = False


__author__ = 'dcristian'


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
    P.mqtt_client.subscribe(topic=P.topic, qos=0)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    json = msg
    try:
        if utils.get_base_location_now_date().minute != P.last_minute:
            P.last_minute = utils.get_base_location_now_date().minute
            P.mqtt_msg_count_per_minute = 0
        P.mqtt_msg_count_per_minute += 1
        P.last_rec = utils.get_base_location_now_date()
        #L.l.debug('Received from client [{}] userdata [{}] msg [{}] at {} '.format(client._client_id,
        #                                                                           userdata, msg.topic,
        #                                                                           utils.get_base_location_now_date()))
        # locate json string
        start = msg.payload.find('{')
        end = msg.payload.rfind('}')
        json = msg.payload[start:end + 1]
        if '"source_host_": "{}"'.format(Constant.HOST_NAME) not in json:
            # ignore messages sent by this host
            x = utils.json2obj(json)
            # if x[Constant.JSON_PUBLISH_SOURCE_HOST] != str(Constant.HOST_NAME):
            start = utils.get_base_location_now_date()
            x['is_event_external'] = True
            dispatcher.send(signal=Constant.SIGNAL_MQTT_RECEIVED, client=client, userdata=userdata, topic=msg.topic, obj=x)
            elapsed = (utils.get_base_location_now_date() - start).total_seconds()
            if elapsed > 5:
                L.l.warning('Command received took {} seconds'.format(elapsed))
            if False:
                if hasattr(x, 'command') and hasattr(x, 'command_id') and hasattr(x, 'host_target'):
                    if x.host_target == Constant.HOST_NAME:
                        L.l.info('Executing command {}'.format(x.command))
                    else:
                        L.l.info("Received command {} for other host {}".format(x, x.host_target))
    except AttributeError as ex:
        L.l.warning('Unknown attribute error in msg {} err {}'.format(json, ex))
    except ValueError as e:
        L.l.warning('Invalid JSON on mqtt, error={}, json={}'.format(e, json))


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
        if P.client_connecting:
            L.l.warning('Mqtt client already in connection process, skipping attempt to connect until done')
            return False
        host_list = [
            #[model_helper.get_param(Constant.P_MQTT_HOST_3), int(model_helper.get_param(Constant.P_MQTT_PORT_3))],
            [model_helper.get_param(Constant.P_MQTT_HOST_1), int(model_helper.get_param(Constant.P_MQTT_PORT_1))],
            #[model_helper.get_param(Constant.P_MQTT_HOST_2), int(model_helper.get_param(Constant.P_MQTT_PORT_2))]
            #[model_helper.get_param(constant.P_MQTT_HOST_3), int(model_helper.get_param(constant.P_MQTT_PORT_3))]
            ]
        P.topic = str(model_helper.get_param(Constant.P_MQTT_TOPIC))
        P.topic_main = str(model_helper.get_param(Constant.P_MQTT_TOPIC_MAIN))
        if P.mqtt_paho_exists:
            P.mqtt_client = mqtt.Client(client_id=Constant.HOST_NAME)
        elif P.mqtt_mosquitto_exists:
            P.mqtt_client = mqtt.Mosquitto(client_id=Constant.HOST_NAME)

        for host_port in host_list:
            P.client_connecting = True
            host = host_port[0]
            port = host_port[1]
            L.l.info('MQTT publisher module initialising, host={} port={}'.format(host, port))
            P.client_connected = False
            retry_count = 0
            while (not P.client_connected) and (retry_count < Constant.ERROR_CONNECT_MAX_RETRY_COUNT):
                try:
                    if P.mqtt_mosquitto_exists:
                        P.mqtt_client.on_connect = on_connect_mosquitto
                    if P.mqtt_paho_exists:
                        P.mqtt_client.on_connect = on_connect_paho
                    P.mqtt_client.on_subscribe = on_subscribe
                    P.mqtt_client.on_unsubscribe = on_unsubscribe
                    # mqtt_client.username_pw_set('user', 'pass')
                    P.mqtt_client.loop_start()
                    P.mqtt_client.connect(host=host, port=port, keepalive=60)
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
                        P.client_connecting = False
                    else:
                        L.l.warning('Timeout connecting to mqtt')
                        retry_count += 1
                except socket.error as ex:
                    L.l.error('mqtt client not connected, err {}, pause and retry {}'.format(ex, retry_count))
                    retry_count += 1
                    time.sleep(Constant.ERROR_CONNECT_PAUSE_SECOND)
                finally:
                    P.client_connecting = False
                    P.last_connect_attempt = utils.get_base_location_now_date()
            if P.client_connected:
                break
            else:
                L.l.warning('Unable to connect to mqtt server {}:{}'.format(host, port))
        if not P.client_connected:
            L.l.critical('MQTT connection not available, all connect attempts failed')
    except Exception as ex:
        L.l.error('Exception on mqtt init, err={}'.format(ex))


def _send_message(txt, topic=None):
    try:
        if topic is None:
            topic = P.topic_main
        # Log.logger.debug('Sending message at {} [{}] '.format(utils.get_base_location_now_date(), txt))
        if P.client_connected:
            P.mqtt_client.publish(topic, "{}".format(txt))
            return True
        else:
            # Log.logger.debug('MQTT client not connected, retrying connect, message to be discarded: {}'.format(txt))
            return False
    except Exception as ex:
        L.l.error('Error sending mqtt message, topic={}, payload={}, err={}'.format(topic, txt, ex), exc_info=True)
        return False
