from main.logger_helper import Log
from main import thread_pool
import ui
import rpusbdisp
import recorder
import gps
import accel
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


def unload():
    Log.logger.info('Dashcam module unloading')
    # ...
    thread_pool.remove_callable(recorder.thread_run)
    thread_pool.remove_callable(gps.thread_run)
    thread_pool.remove_callable(accel.thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.info('Dashcam module initialising')
    thread_pool.add_interval_callable(recorder.thread_run, run_interval_second=60)
    thread_pool.add_interval_callable(gps.thread_run, run_interval_second=60)
    thread_pool.add_interval_callable(accel.thread_run, run_interval_second=0.2)
    global initialised
    initialised = True
    ui.init()


if __name__ == '__main__':
    pass
