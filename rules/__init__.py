__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
from main.admin import thread_pool
import rules

initialised=False

def rule1():
    pass

def unload():
    logger.info('Template module unloading')
    #...
    thread_pool.remove_callable(rules.thread_run)
    global initialised
    initialised = False

def init():
    logger.info('Template module initialising')
    thread_pool.add_callable(rules.thread_run, run_interval_second=60)
    global initialised
    initialised = True

if __name__ == '__main__':
    rules.thread_run()