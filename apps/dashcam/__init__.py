from main.logger_helper import L
from main import thread_pool
from common import Constant
import ui
from pydispatch import dispatcher
#import rpusbdisp
import recorder
from recorder import uploader
import gps
import accel
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


class P:
    battery_max_voltage = 4.1
    #battery_min_voltage = 3.5
    battery_warn_voltage = 3.6
    battery_sleep_voltage = 3.4
    battery_shutdown_voltage = 3.4
    battery_warn_current = 1000


def unload():
    L.l.info('Dashcam module unloading')
    # ...
    thread_pool.remove_callable(recorder.thread_run)
    recorder.unload()
    thread_pool.remove_callable(gps.thread_run)
    gps.unload()
    thread_pool.remove_callable(accel.thread_run)
    accel.unload()
    global initialised
    initialised = False


def _battery_stat(battery, voltage, current, power):
    if voltage <= P.battery_warn_voltage:
        L.l.warning("Battery voltage is very low at {}".format(voltage))
        pass
    if voltage <= P.battery_shutdown_voltage:
        L.l.warning("Battery voltage is too low at {}, shutting down system".format(voltage))
        pass
    L.l.info("Battery {} v={} c={} p={}".format(battery, voltage, current, power))


def thread_run():
    uploader.thread_run()
    gps.thread_run()


def init():
    L.l.info('Dashcam module initialising')
    recorder.init()
    thread_pool.add_interval_callable(recorder.thread_run, run_interval_second=recorder.thread_tick)
    thread_pool.add_interval_callable(thread_run, run_interval_second=10)
    gps.init()
    dispatcher.connect(_battery_stat, signal=Constant.SIGNAL_BATTERY_STAT, sender=dispatcher.Any)
    #accel.init()
    #thread_pool.add_interval_callable(accel.thread_run, run_interval_second=0.5)
    #ui.init()
    global initialised
    initialised = True


if __name__ == '__main__':
    pass
