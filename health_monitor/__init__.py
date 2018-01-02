__author__ = 'dcristian'

from main import thread_pool
import health_monitor_loop
from main.logger_helper import L

initialised=False

def unload():
    global initialised
    initialised = False
    thread_pool.remove_callable(health_monitor_loop.thread_run)

def init():
    L.l.debug('Monitor module initialising')
    health_monitor_loop.init()
    thread_pool.add_interval_callable_progress(func=health_monitor_loop.thread_run, run_interval_second=120,
                                     progress_func=health_monitor_loop.get_progress)
    global initialised
    #health_monitor_loop.thread_run()
    initialised = True
