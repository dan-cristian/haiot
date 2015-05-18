__author__ = 'dcristian'
from main import logger
from pydispatch import dispatcher
import datetime
from main.admin import db, models
import alarm_loop
from main.admin import thread_pool
from common import constant, utils
from main.admin.model_helper import commit

initialised=False

def handle_event_alarm(gpio_pin_code='', direction='', pin_value=''):
    pass
    zonealarm=models.ZoneAlarm.query.filter_by(gpio_pin_code=gpio_pin_code).first()
    if zonealarm:
        zonealarm.alarm_status = pin_value
        zonealarm.updated_on = utils.get_base_location_now_date()
        zonealarm.notify_transport_enabled= False
        commit()
    else:
        logger.warning('Unexpected mising zone alarm for gpio code {}'.format(gpio_pin_code))

def unload():
    logger.info('Alarm module unloading')
    global initialised
    dispatcher.disconnect(dispatcher.connect(handle_event_alarm, signal=constant.SIGNAL_GPIO, sender=dispatcher.Any))
    thread_pool.remove_callable(alarm_loop.thread_run)
    initialised = False

def init():
    logger.info('Alarm module initialising')
    alarm_loop.init()
    thread_pool.add_callable(alarm_loop.thread_run)
    dispatcher.connect(handle_event_alarm, signal=constant.SIGNAL_GPIO, sender=dispatcher.Any)
    global initialised
    initialised = True
