__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import L
from main import thread_pool
import ddns_run

initialised = False


def unload():
    L.l.info('DDNS module unloading')
    # ...
    thread_pool.remove_callable(ddns_run.thread_run)
    global initialised
    initialised = False


def init():
    L.l.info('DDNS module initialising')
    thread_pool.add_interval_callable(ddns_run.thread_run, run_interval_second=600)
    global initialised
    initialised = True
