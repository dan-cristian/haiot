__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import requests
import schedule
import threading
import prctl
from main.logger_helper import L
from main import thread_pool

initialised = False


# fixme: replace schedule with apschedule
def openshift_keepalive():
    try:
        # if variable.NODE_THIS_IS_MASTER_OVERALL:
        # req = requests.get('http://iot-dancristian.rhcloud.com')
        pass
    except Exception as ex:
        L.l.info('Error keeping openshift alive, err={}'.format(ex))


def setup_tasks():
    schedule.every(1).minutes.do(openshift_keepalive)


def thread_run():
    prctl.set_name("cron")
    threading.current_thread().name = "cron"
    schedule.run_pending()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    schedule.clear()


def init():
    L.l.info('cron module initialising')
    setup_tasks()
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    global initialised
    initialised = True
