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
from collections import namedtuple
from main.admin import models
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


class P:
    power_monitor_list = {}


def unload():
    L.l.info('Dashcam module unloading')
    # ...
    thread_pool.remove_callable(recorder.thread_run)
    thread_pool.remove_callable(thread_run)
    thread_pool.remove_callable(accel.thread_run)
    recorder.unload()
    gps.unload()
    accel.unload()
    global initialised
    initialised = False


def _battery_stat(battery_name, voltage, current, power):
    if battery_name in P.power_monitor_list:
        power_monitor = P.power_monitor_list[battery_name]
        if voltage <= power_monitor.critical_voltage:
            L.l.warning("Battery {} voltage is too low at {}".format(battery_name, voltage))
            # shutdown_system
        if voltage <= power_monitor.warn_voltage:
            L.l.warning("Battery {} voltage is very low at {}".format(battery_name, voltage))
            pass
        if current >= power_monitor.warn_current:
            L.l.warning("Battery {} current used is very high at {}".format(battery_name, current))
            pass
        L.l.info("Battery {} v={} c={} p={}".format(battery_name, voltage, current, power))
    else:
        L.l.info("Unknown battery reading received, name={}".format(battery_name))


def _battery_init():
    power_list = models.PowerMonitor().query_all()
    for power in power_list:
        if power.host_name == Constant.HOST_NAME:
            P.power_monitor_list[power.name] = power


def thread_run():
    uploader.thread_run()
    gps.thread_run()


def init():
    L.l.info('Dashcam module initialising')
    recorder.init()
    gps.init()
    _battery_init()
    accel.init()
    thread_pool.add_interval_callable(recorder.thread_run, run_interval_second=recorder.thread_tick)
    thread_pool.add_interval_callable(thread_run, run_interval_second=10)
    thread_pool.add_interval_callable(accel.thread_run, run_interval_second=0.5)
    dispatcher.connect(_battery_stat, signal=Constant.SIGNAL_BATTERY_STAT, sender=dispatcher.Any)
    #ui.init()
    global initialised
    initialised = True


if __name__ == '__main__':
    pass
