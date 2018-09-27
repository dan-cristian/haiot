import threading
import prctl
import subprocess
from pydispatch import dispatcher
from main.logger_helper import L
from main import thread_pool
from common import Constant

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    last_usb_out = None

    def __init__(self):
        pass


def _check_usb_change():
    if Constant.IS_OS_LINUX():
        out = subprocess.check_output(['lsusb']).split('\n')
        if P.last_usb_out is not None and P.last_usb_out != out:
            P.last_usb_out = out
            return True
        else:
            return False
    else:
        # todo: implement a Windows version
        return False


def thread_run():
    prctl.set_name("usb")
    threading.current_thread().name = "usb"
    if _check_usb_change():
        dispatcher.send(Constant.SIGNAL_USB_DEVICE_CHANGE)
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Processed usb'


def unload():
    L.l.info('Usb module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('usb module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    P.initialised = True
