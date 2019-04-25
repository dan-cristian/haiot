from main.logger_helper import L
from common import fix_module
while True:
    try:
        import prctl
        break
    except ImportError as iex:
        if not fix_module(iex):
            break
import threading
import transport.mqtt_io
from common import utils
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
            start_len = len(P.send_json_queue)
            # FIXME: complete this, will potentially accumulate too many requests
            for [json, topic] in list(P.send_json_queue):
                res = transport.mqtt_io._send_message(json, topic)
                if res:
                    P.send_json_queue.remove([json, topic])
                else:
                    L.l.info('Failed to send mqtt message, res={}'.format(res))
            end_len = len(P.send_json_queue)
            if end_len > 10:
                L.l.warning("{} messages are pending for transport, start was {}".format(end_len, start_len))
        else:
            elapsed = (utils.get_base_location_now_date() - mqtt_io.P.last_connect_attempt).total_seconds()
            if elapsed > 10:
                L.l.info("Initialising mqtt as message needs to be sent, elapsed={}".format(elapsed))
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
    thread_pool.add_interval_callable(thread_run, run_interval_second=0.2)
    mqtt_io.init()
    P.initialised = True
