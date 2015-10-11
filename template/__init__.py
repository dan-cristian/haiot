__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import Log
from main import thread_pool
import template_run

initialised=False

def unload():
    Log.logger.info('Template module unloading')
    #...
    thread_pool.remove_callable(template_run.thread_run)
    global initialised
    initialised = False

def init():
    Log.logger.info('Template module initialising')
    thread_pool.add_interval_callable(template_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True

if __name__ == '__main__':
    template_run.thread_run()