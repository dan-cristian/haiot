import time
import socket
from main import thread_pool
from main.logger_helper import L
from main.admin import model_helper
from common import Constant, utils
import receiver
import sender

mqtt_mosquitto_exists = False
mqtt_paho_exists = False

#try:
#    import mosquitto as mqtt
#    mqtt_mosquitto_exists = True
#except Exception:
mqtt_mosquitto_exists = False

try:
    if not mqtt_mosquitto_exists:
        import paho.mqtt.client as mqtt
        mqtt_paho_exists = True
except Exception:
    mqtt_paho_exists = False


__author__ = 'dcristian'
initialised=False
client_connected = False
client_connecting = False
mqtt_msg_count_per_minute = 0
last_connect_attempt = None


class P:
    topic = 'no_topic_defined'
    topic_main = 'no_main_topic_defined'
    mqtt_client = None


# The callback for when the client receives a CONNACK response from the server.
def on_connect_paho(client, userdata, flags, rc):
    L.l.info("Connected to mqtt paho with result code " + str(rc))
    global client_connected
    client_connected = True
    subscribe()


def on_connect_mosquitto(mosq, userdata, rc):
    L.l.info("Connected to mqtt mosquitto with result code " + str(rc))
    subscribe()


def on_disconnect(client, userdata, rc):
    if rc != 0:
        L.l.warning("Unexpected disconnection from mqtt")
    L.l.warning("Disconnected from mqtt")
    global client_connected
    client_connected = False


def on_subscribe(client, userdata, mid, granted_qos):
    global client_connected
    client_connected = True


#def on_subscribe(client, userdata, mid, granted_qos):
#    Log.logger.info('Subscribed as user {} mid {} qos {}'.format(str(userdata), str(mid), str(granted_qos)))


def on_unsubscribe(client, userdata, mid):
    global client_connected
    client_connected = False


def subscribe():
    L.l.info('Subscribing to mqtt topic={}'.format(P.topic))
    P.mqtt_client.username_pw_set(Constant.HOST_NAME)
    P.mqtt_client.user_data_set(Constant.HOST_NAME + " userdata")
    P.mqtt_client.will_set(Constant.HOST_NAME + " DIE")
    P.mqtt_client.subscribe(topic=P.topic, qos=0)


def unload():
    global mqtt_paho_exists, mqtt_mosquitto_exists
    P.mqtt_client.unsubscribe(P.topic)
    try:
        P.mqtt_client.loop_stop()
    except Exception as ex:
        L.l.warning('Unable to stop mqtt loop, err {}'.format(ex))
    P.mqtt_client.disconnect()


def init():
    if mqtt_mosquitto_exists:
        L.l.info("INIT, Using mosquitto as mqtt client")
    elif mqtt_paho_exists:
        L.l.info("INIT, Using paho as mqtt client")
    else:
        L.l.critical("No mqtt client enabled via import")
        raise Exception("No mqtt client enabled via import")

    # not a good ideea to set a timeout as it will crash pigpio_gpio callback
    # socket.setdefaulttimeout(10)
    try:
        global client_connecting
        if client_connecting:
            L.l.warning('Mqtt client already in connection process, skipping attempt to connect until done')
            return
        host_list = [
            #[model_helper.get_param(Constant.P_MQTT_HOST_3), int(model_helper.get_param(Constant.P_MQTT_PORT_3))],
            [model_helper.get_param(Constant.P_MQTT_HOST_1), int(model_helper.get_param(Constant.P_MQTT_PORT_1))],
            #[model_helper.get_param(Constant.P_MQTT_HOST_2), int(model_helper.get_param(Constant.P_MQTT_PORT_2))]
            #[model_helper.get_param(constant.P_MQTT_HOST_3), int(model_helper.get_param(constant.P_MQTT_PORT_3))]
            ]
        P.topic = str(model_helper.get_param(Constant.P_MQTT_TOPIC))
        P.topic_main = str(model_helper.get_param(Constant.P_MQTT_TOPIC_MAIN))
        if mqtt_paho_exists:
            P.mqtt_client = mqtt.Client()
        elif mqtt_mosquitto_exists:
            P.mqtt_client = mqtt.Mosquitto()

        global client_connected
        global initialised
        for host_port in host_list:
            client_connecting = True
            host = host_port[0]
            port = host_port[1]
            L.l.info('MQTT publisher module initialising, host={} port={}'.format(host, port))
            client_connected=False
            retry_count = 0
            while (not client_connected) and (retry_count < Constant.ERROR_CONNECT_MAX_RETRY_COUNT):
                try:
                    if mqtt_mosquitto_exists:
                        P.mqtt_client.on_connect = on_connect_mosquitto
                    if mqtt_paho_exists:
                        P.mqtt_client.on_connect = on_connect_paho
                    P.mqtt_client.on_subscribe = on_subscribe
                    P.mqtt_client.on_unsubscribe = on_unsubscribe
                    # mqtt_client.username_pw_set('user', 'pass')
                    P.mqtt_client.loop_start()
                    P.mqtt_client.connect(host=host, port=port, keepalive=60)
                    seconds_lapsed = 0
                    while not client_connected and seconds_lapsed < 10:
                        time.sleep(1)
                        seconds_lapsed += 1
                    if client_connected:
                        # mqtt_client.on_message = receiver.on_message
                        P.mqtt_client.message_callback_add(P.topic_main, receiver.on_message)
                        P.mqtt_client.on_disconnect = on_disconnect
                        thread_pool.add_interval_callable(receiver.thread_run, run_interval_second=10)
                        # mqtt_client.loop_start()
                        initialised = True
                        client_connecting = False
                    else:
                        L.l.warning('Timeout connecting to mqtt')
                        retry_count += 1
                except socket.error as ex:
                    L.l.error('mqtt client not connected, err {}, pause and retry {}'.format(ex, retry_count))
                    retry_count += 1
                    time.sleep(Constant.ERROR_CONNECT_PAUSE_SECOND)
                finally:
                    client_connecting = False
                    global last_connect_attempt
                    last_connect_attempt = utils.get_base_location_now_date()
            if client_connected:
                break
            else:
                L.l.warning('Unable to connect to mqtt server {}:{}'.format(host, port))
        if not client_connected:
            L.l.critical('MQTT connection not available, all connect attempts failed')
    except Exception as ex:
        L.l.error('Exception on mqtt init, err={}'.format(ex))

