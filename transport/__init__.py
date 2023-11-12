from main.logger_helper import L
from common import fix_module
while True:
    try:
        import prctl
        from pydispatch import dispatcher
        break
    except ImportError as iex:
        if not fix_module(iex):
            break
import threading
import transport.mqtt_io
from pydispatch import dispatcher
from common import utils, Constant
from transport import mqtt_io
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    send_json_queue = []
    mqtt_send_lock = threading.Lock()
    send_thread_lock = threading.Lock()
    recv_thread_lock = threading.Lock()
    thread_recv = None
    thread_send = None

    def __init__(self):
        pass


# exit fast to avoid blocking db commit request?
def send_message_json(json=''):
    P.send_json_queue.append([json, mqtt_io.P.topic_main])
    # if P.send_thread_lock.locked():
    #    P.send_thread_lock.release()


def send_message_topic(topic, json):
    P.send_json_queue.append([json, topic])
    if P.recv_thread_lock.locked():
        P.recv_thread_lock.release()


def thread_run_send():
    prctl.set_name("mqtt_send")
    threading.current_thread().name = "mqtt_send"
    P.thread_send = threading.current_thread()
    if mqtt_io.P.client_connected:
        start_len = len(P.send_json_queue)
        if start_len > 50:
            L.l.info('Mqtt SEND len={}'.format(start_len))
        # FIXME: complete this, will potentially accumulate too many requests
        P.mqtt_send_lock.acquire()
        for [json, topic] in list(P.send_json_queue):
            res = transport.mqtt_io._send_message(json, topic)
            if res:
                P.send_json_queue.remove([json, topic])
            else:
                L.l.info('Failed to send mqtt message, res={}'.format(res))
        P.mqtt_send_lock.release()
        end_len = len(P.send_json_queue)
        if end_len > 10:
            L.l.warning("{} messages are pending for transport, start was {}".format(end_len, start_len))
    else:
        elapsed = (utils.get_base_location_now_date() - mqtt_io.P.last_connect_attempt).total_seconds()
        if elapsed > 10:
            L.l.info("Initialising mqtt as message needs to be sent, elapsed={}".format(elapsed))
            mqtt_io.init()
    prctl.set_name("idle_mqtt_send")
    threading.current_thread().name = "idle_mqtt_send"


def thread_run_recv():
    prctl.set_name("mqtt_recv")
    threading.current_thread().name = "mqtt_recv"
    P.thread_recv = threading.current_thread()
    obj = None
    try:
        if len(mqtt_io.P.received_mqtt_list) > 10:
            L.l.info('Mqtt RECV len={}'.format(len(mqtt_io.P.received_mqtt_list)))
        if len(mqtt_io.P.received_mqtt_list) == 0:
            delta = (utils.get_base_location_now_date() - mqtt_io.P.last_rec).total_seconds()
            if delta > 60:
                L.l.warning('No mqtt received since {} sec'.format(delta))
        for obj in list(mqtt_io.P.received_mqtt_list):
            mqtt_io.P.received_mqtt_list.remove(obj)
            dispatcher.send(signal=Constant.SIGNAL_MQTT_RECEIVED, obj=obj)
    except Exception as ex:
        L.l.error('Error on mqtt receive process, err={}, obj={}'.format(ex, obj))
    finally:
        prctl.set_name("idle_mqtt_recv")
        threading.current_thread().name = "idle_mqtt_recv"


def unload():
    from main import thread_pool
    L.l.info('Transport unloading')
    # ...
    thread_pool.remove_callable(thread_run_send)
    P.initialised = False


def init():
    from main import thread_pool
    L.l.info('Transport initialising')
    thread_pool.add_interval_callable(thread_run_send, run_interval_second=0.1)
    thread_pool.add_interval_callable(thread_run_recv, run_interval_second=0.1)
    mqtt_io.init()
    # utils.init_debug()
    P.initialised = True
