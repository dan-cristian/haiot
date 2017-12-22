__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import Log
from main import thread_pool, IS_STANDALONE_MODE
import node_run

initialised=False


def unload():
    #...
    thread_pool.remove_callable(node_run.thread_run)
    global initialised
    initialised = False


def init():
    if not IS_STANDALONE_MODE:
        Log.logger.info('Node module initialising')
        thread_pool.add_interval_callable_progress(node_run.thread_run, run_interval_second=30,
                                                   progress_func=node_run.get_progress)
        global initialised
        initialised = True
    else:
        Log.logger.info('Skipping node module initialising, standalone mode')


if __name__ == '__main__':
    node_run.thread_run()