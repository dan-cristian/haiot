__author__ = 'dcristian'

from main.admin import thread_pool
import health_monitor_loop, logging

def init():
    logging.info('Monitor module initialising')
    health_monitor_loop.init()
    thread_pool.add_callable(health_monitor_loop.thread_run)
    thread_pool.set_exec_interval(health_monitor_loop.thread_run, 30)

if __name__ == '__main__':
    init()