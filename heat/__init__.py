__author__ = 'dcristian'

import heat_loop
import logging
from main.admin import thread_pool
initialised=False

def unload():
    logging.info('Heat module unloading')
    global initialised
    initialised = False
    thread_pool.remove_callable(heat_loop.thread_run)

def init():
    logging.info('Heat module initialising')
    thread_pool.add_callable(heat_loop.thread_run, 30)
    global initialised
    initialised = True
