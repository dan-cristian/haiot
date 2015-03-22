__author__ = 'dcristian'

from main.admin import thread_pool
import health_monitor_loop, logging

initialised=False

def unload():
    global initialised
    initialised = False
    thread_pool.remove_callable(health_monitor_loop.thread_run)

def init():
    logging.info('Monitor module initialising')
    health_monitor_loop.init()
    thread_pool.add_callable(health_monitor_loop.thread_run)
    thread_pool.set_exec_interval(health_monitor_loop.thread_run, 30)
    global initialised
    initialised = True

if __name__ == '__main__':
    init()