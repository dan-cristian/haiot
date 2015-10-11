__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import Log
from main import thread_pool
import ddns_run

initialised=False

def unload():
    Log.logger.info('DDNS module unloading')
    #...
    thread_pool.remove_callable(ddns_run.thread_run)
    global initialised
    initialised = False

def init():
    Log.logger.info('DDNS module initialising')
    thread_pool.add_interval_callable(ddns_run.thread_run, run_interval_second=120)
    global initialised
    initialised = True
