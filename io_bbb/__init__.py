__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging

from main.admin import thread_pool
import io_bbb_run

initialised=False

def unload():
    #...
    thread_pool.remove_callable(io_bbb_run.thread_run)
    global initialised
    initialised = False

def init():
    logging.info('Beaglebone IO module initialising')
    try:
        io_bbb_run.init()
        thread_pool.add_callable(io_bbb_run.thread_run, run_interval_second=5)
        global initialised
        initialised = True
    except Exception, ex:
        logging.critical('Module io_bbb not initialised, err={}'.format(ex))

if __name__ == '__main__':
    io_bbb_run.thread_run()