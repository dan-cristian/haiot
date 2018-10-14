import threading
import prctl
from common import Constant, utils
from main.logger_helper import L
from main.admin import model_helper
from main import thread_pool
from transport import mqtt_io


class P:
    initialised = False
    sonoff_topic = None
    check_period = 5

    def __init__(self):
        pass


def mqtt_on_message(client, userdata, msg):
    L.l.info("Client={} data={} msg={}".format(client, userdata, msg))


def mqtt_on_message_2(client, userdata, msg):
    L.l.info("Client2={} data={} msg={}".format(client, userdata, msg))


def thread_run():
    prctl.set_name("sonoff")
    threading.current_thread().name = "sonoff"

    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Sonoff module initialising')
    P.sonoff_topic_1 = str(model_helper.get_param(Constant.P_MQTT_TOPIC_SONOFF_1))
    P.sonoff_topic_2 = str(model_helper.get_param(Constant.P_MQTT_TOPIC_SONOFF_2))
    mqtt_io.P.mqtt_client.message_callback_add(P.sonoff_topic_1, mqtt_on_message)
    mqtt_io.P.mqtt_client.message_callback_add(P.sonoff_topic_2, mqtt_on_message_2)
    thread_pool.add_interval_callable(thread_run, P.check_period)
