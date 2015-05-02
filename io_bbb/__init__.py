__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
from main.admin import thread_pool
import io_bbb_run

initialised=False

def unload():
    #...
    thread_pool.remove_callable(io_bbb_run.thread_run)
    global initialised
    initialised = False

def init():
    logger.info('Beaglebone IO module initialising')
    try:
        io_bbb_run.init()
        thread_pool.add_callable(io_bbb_run.thread_run, run_interval_second=2)
        global initialised
        initialised = True
    except Exception, ex:
        logger.critical('Module io_bbb not initialised, err={}'.format(ex))
