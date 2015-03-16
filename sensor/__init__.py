__author__ = 'dcristian'

#! venv/bin/python

from main.admin import thread_pool
import owsensor_loop, logging

def init():
    logging.info('Sensor module initialising')
    owsensor_loop.init()
    thread_pool.add_callable(owsensor_loop.thread_run)

if __name__ == '__main__':
    init()