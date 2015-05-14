__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
import transport_run
from transport import mqtt_io

initialised = False

def send_message_json(json=''):
    mqtt_io.sender.send_message(json)

def send_message_obj(obj=''):
    pass


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
    #thread_pool.add_callable(transport_run.thread_run, run_interval_second=60)
    mqtt_io.init()
    global initialised
    initialised = True
