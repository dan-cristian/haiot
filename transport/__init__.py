__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
import transport_run
from transport import mqtt_io

initialised = False
__send_json_queue = []

#exit fast to avoid blocking db commit request?
def send_message_json(json=''):
    __send_json_queue.append(json)

def send_message_obj(obj=''):
    pass

def thread_run():
    #FIXME: complete this, will potentially accumulate too many requests
    for json in __send_json_queue:
        if mqtt_io.sender.send_message(json):
            __send_json_queue.remove(json)
    if len(__send_json_queue) > 20:
        logger.warning("{} messages are pending in transport send queue".format(len(__send_json_queue)))

def unload():
    from main.admin import thread_pool
    logger.info('Transport unloading')
    # ...
    thread_pool.remove_callable(transport_run.thread_run)
    global initialised
    initialised = False


def init():
    from main.admin import thread_pool
    logger.info('Transport initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    mqtt_io.init()
    global initialised
    initialised = True
