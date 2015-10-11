__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import Log, thread_pool
import test_run
from main.admin import thread_pool
initialised = False


def unload():
    #...
    #thread_pool.remove_callable(test_run.thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.info('TEST module initialising')
    thread_pool.add_interval_callable(test_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True


if __name__ == '__main__':
    test_run.thread_run()