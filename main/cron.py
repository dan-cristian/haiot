__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import requests
import schedule
from main.logger_helper import Log
from main import thread_pool

initialised = False


# fixme: replace schedule with apschedule
def openshift_keepalive():
    try:
        # if variable.NODE_THIS_IS_MASTER_OVERALL:
        #req = requests.get('http://iot-dancristian.rhcloud.com')
        pass
    except Exception, ex:
        Log.logger.info('Error keeping openshift alive, err={}'.format(ex))


def setup_tasks():
    schedule.every(1).minutes.do(openshift_keepalive)


def thread_run():
    schedule.run_pending()


def unload():
    schedule.clear()


def init():
    Log.logger.info('cron module initialising')
    setup_tasks()
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    global initialised
    initialised = True
