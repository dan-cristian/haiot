__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import requests
import schedule
from main import logger
from main.admin import thread_pool
from common import variable

initialised = False
def openshift_keepalive():
    try:
        if variable.NODE_THIS_IS_MASTER_OVERALL:
            req = requests.get('http://iot-dancristian.rhcloud.com')
    except Exception, ex:
        logger.info('Error keeping openshift alive, err={}'.format(ex))

def setup_tasks():
    schedule.every(1).minutes.do(openshift_keepalive)

def thread_run():
    schedule.run_pending()

def init():
    logger.info('cron module initialising')
    setup_tasks()
    thread_pool.add_callable(thread_run, run_interval_second=60)
    global initialised
    initialised = True

