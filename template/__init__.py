import threading
import prctl
from main.logger_helper import L
from main import thread_pool

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False

    def __init__(self):
        pass


def thread_run():
    prctl.set_name("")
    threading.current_thread().name = ""
    #
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Processed template_run'


def unload():
    L.l.info('Template module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Template module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    P.initialised = True
    # dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)
    # dispatcher.send(Constant.SIGNAL_USB_DEVICE_CHANGE)
