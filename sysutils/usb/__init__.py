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
    if Constant.is_os_linux():
        try:
            out = subprocess.check_output(['lsusb']).decode('utf-8').split('\n')
            if P.last_usb_out is not None and P.last_usb_out != out:
                P.last_usb_out = out
                return True
        except Exception as ex:
            L.l.warning('lsusb returned {}'.format(ex))
    # todo: implement a Windows version
    # https://stackoverflow.com/questions/4273252/detect-inserted-usb-on-windows
    return False


def thread_run():
    prctl.set_name("usb")
    threading.current_thread().name = "usb"
    if _check_usb_change():
        dispatcher.send(Constant.SIGNAL_USB_DEVICE_CHANGE)
    prctl.set_name("idle_usb")
    threading.current_thread().name = "idle_usb"
    return 'Processed usb'


def unload():
    L.l.info('Usb module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('usb module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    P.initialised = True
