import threading
import prctl
import transport.mqtt_io
from common import utils
from main.logger_helper import L
from transport import mqtt_io

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    send_json_queue = []
    mqtt_lock = threading.Lock()

    def __init__(self):
        pass


# exit fast to avoid blocking db commit request?
def send_message_json(json=''):
    P.send_json_queue.append([json, mqtt_io.P.topic_main])


def send_message_topic(json='', topic=None):
    P.send_json_queue.append([json, topic])


def thread_run():
    prctl.set_name("transport")
    threading.current_thread().name = "transport"
    P.mqtt_lock.acquire()
    try:
        if mqtt_io.P.client_connected:
            # FIXME: complete this, will potentially accumulate too many requests
            for [json, topic] in list(P.send_json_queue):
                if transport.mqtt_io._send_message(json, topic):
                    P.send_json_queue.remove([json, topic])
            if len(P.send_json_queue) > 20:
                L.l.warning("{} messages are pending in transport send queue".format(len(P.send_json_queue)))
        else:
            elapsed = (utils.get_base_location_now_date() - mqtt_io.P.last_connect_attempt).total_seconds()
            if elapsed > 10:
                mqtt_io.init()
    finally:
        P.mqtt_lock.release()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    from main import thread_pool
    L.l.info('Transport unloading')
    # ...
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    from main import thread_pool
    L.l.info('Transport initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    mqtt_io.init()
    P.initialised = True
