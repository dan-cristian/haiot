__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import L, thread_pool
from main import thread_pool
from main.admin import models

initialised = False


def unload():
    # ...
    # thread_pool.remove_callable(test_run.thread_run)
    global initialised
    initialised = False


def init():
    L.l.info('TEST module initialising')
    sensor_address = "ZMNHTDx Smart meter S4 S5 S6:2"
    current_record = models.Sensor.query.filter_by(address=sensor_address).first()
    # thread_pool.add_interval_callable(test_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True


