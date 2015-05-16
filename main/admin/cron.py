__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from crontab import CronTab
from main import logger
from main.admin import thread_pool

initialised = False
def __cron():
    pass

def thread_run():
    logger.debug('Processing cron rrun')
    __cron()
    return 'Processed ddns_run'

def init():
    logger.info('cron module initialising')
    thread_pool.add_callable(thread_run, run_interval_second=60)
    global initialised
    initialised = True

