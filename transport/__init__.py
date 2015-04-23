__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
from main.admin import thread_pool
import transport_run
import transport.mqtt_io

initialised=False

def send_message_json(json=''):
    transport.mqtt_io.sender.send_message(json)
    pass


def send_message_obj(obj=''):
    pass

def unload():
    logger.info('Template transport unloading')
    #...
    thread_pool.remove_callable(transport_run.thread_run)
    global initialised
    initialised = False

def init():
    logger.info('Template transport initialising')
    thread_pool.add_callable(transport_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
