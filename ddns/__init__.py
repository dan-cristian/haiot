__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging

from main.admin import thread_pool
import ddns_run

initialised=False

def unload():
    logging.info('DDNS module unloading')
    #...
    thread_pool.remove_callable(ddns_run.thread_run)
    global initialised
    initialised = False

def init():
    logging.info('DDNS module initialising')
    thread_pool.add_callable(ddns_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
