__author__ = 'dcristian'

#! venv/bin/python

from main.admin import thread_pool
import logging
import math
import owsensor_loop
import rfxcom_run
initialised=False

def round_sensor_value(val):
    return math.ceil(float(val)*10)/10

def unload():
    #...
    thread_pool.remove_callable(owsensor_loop.thread_run)
    thread_pool.remove_callable(rfxcom_run.thread_run)
    global initialised
    initialised = False

def init():
    logging.info('Sensor module initialising')
    if owsensor_loop.init():
        thread_pool.add_callable(owsensor_loop.thread_run, run_interval_second=15)
    if rfxcom_run.init():
        thread_pool.add_callable(rfxcom_run.thread_run, run_interval_second=15)
    global initialised
    initialised = True
