__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import L
from main import thread_pool
import ddns_run


class P:
    initialised = False

    def __init__(self):
        pass


def unload():
    L.l.info('DDNS module unloading')
    thread_pool.remove_callable(ddns_run.thread_run)
    P.initialised = False


def init():
    L.l.info('DDNS module initialising')
    thread_pool.add_interval_callable(ddns_run.thread_run, run_interval_second=600)
    P.initialised = True
