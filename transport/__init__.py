import threading
from main.logger_helper import Log
import transport_run
from transport import mqtt_io

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


initialised = False
__send_json_queue = []
__mqtt_lock = threading.Lock()


# exit fast to avoid blocking db commit request?
def send_message_json(json=''):
    __send_json_queue.append(json)


def send_message_obj(obj=''):
    pass


def thread_run():
    global __mqtt_lock
    __mqtt_lock.acquire()
    try:
        # FIXME: complete this, will potentially accumulate too many requests
        for json in __send_json_queue:
            #  Log.logger.info("Sending mqtt {}".format(json))
            if mqtt_io.sender.send_message(json):
                __send_json_queue.remove(json)
        if len(__send_json_queue) > 20:
            Log.logger.warning("{} messages are pending in transport send queue".format(len(__send_json_queue)))
    finally:
        __mqtt_lock.release()


def unload():
    from main import thread_pool
    Log.logger.info('Transport unloading')
    # ...
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False


def init():
    from main import thread_pool
    Log.logger.info('Transport initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    mqtt_io.init()
    global initialised
    initialised = True
