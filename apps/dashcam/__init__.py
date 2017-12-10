from main.logger_helper import Log
from main import thread_pool
import dashcam_run
import dashcam_ui

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


def unload():
    Log.logger.info('Dashcam module unloading')
    # ...
    thread_pool.remove_callable(dashcam_run.thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.info('Dashcam module initialising')
    thread_pool.add_interval_callable(dashcam_run.thread_run, run_interval_second=60)
    global initialised
    initialised = True
    dashcam_ui.init()


if __name__ == '__main__':
    dashcam_run.thread_run()
