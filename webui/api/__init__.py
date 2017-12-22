__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


from main.logger_helper import Log
from main import thread_pool
import api_v1

initialised = False


def unload():
    Log.logger.info('API module unloading')
    # ...
    # thread_pool.remove_callable(template_run.thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.debug('API module initialising')
    # thread_pool.add_interval_callable(template_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
