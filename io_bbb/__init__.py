__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging

from main.admin import thread_pool
import io_bbb

initialised=False

def unload():
    #...
    thread_pool.remove_callable(io_bbb.thread_run)
    global initialised
    initialised = False

def init():
    logging.info('Beaglebone IO module initialising')
    io_bbb.init()
    thread_pool.add_callable(io_bbb.thread_run, run_interval_second=5)
    global initialised
    initialised = True

if __name__ == '__main__':
    io_bbb.thread_run()