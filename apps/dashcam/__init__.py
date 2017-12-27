from main.logger_helper import Log
from main import thread_pool
import ui
#import rpusbdisp
import recorder
from recorder import uploader
import gps
import accel
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


def unload():
    Log.logger.info('Dashcam module unloading')
    # ...
    thread_pool.remove_callable(recorder.thread_run)
    recorder.unload()
    thread_pool.remove_callable(gps.thread_run)
    gps.unload()
    thread_pool.remove_callable(accel.thread_run)
    accel.unload()
    global initialised
    initialised = False


def init():
    Log.logger.info('Dashcam module initialising')
    recorder.init()
    thread_pool.add_interval_callable(recorder.thread_run, run_interval_second=1)
    thread_pool.add_interval_callable(uploader.thread_run, run_interval_second=10)
    gps.init()
    thread_pool.add_interval_callable(gps.thread_run, run_interval_second=10)
    #accel.init()
    #thread_pool.add_interval_callable(accel.thread_run, run_interval_second=0.5)
    #ui.init()
    global initialised
    initialised = True

if __name__ == '__main__':
    pass
