__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging

from main.admin import thread_pool
import node_run

initialised=False

def unload():
    #...
    thread_pool.remove_callable(node_run.thread_run)
    global initialised
    initialised = False

def init():
    logging.info('Node module initialising')
    #node_run.init()
    thread_pool.add_callable(node_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True

if __name__ == '__main__':
    node_run.thread_run()