__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import time

from main.logger_helper import Log
from main import app
from main.admin import models

try:
    #sometimes I get "ImportError: cannot import name scheduler" so trying two import methods
    from rule import scheduler
except Exception:
    from . import scheduler
#two types of rules are supported:
#1: cron based rules
#https://apscheduler.readthedocs.org/en/latest/userguide.html#adding-jobs
#https://apscheduler.readthedocs.org/en/v2.1.2/cronschedule.html
#2: value changed rules, first obj parameter is mandatory. function will execute for object changed
# that have type=obj

####### VALUE TRIGGER RULES ########
def rule_node(obj = models.Node(), field_changed_list = []):
    return 'rule node ok'

#min & max temperatures
def rule_sensor_temp_target(obj = models.Sensor(), field_changed_list = []):
    temp = obj.temperature
    return 'rule temp ok'

######## CRON RULES ################
try:

    #@scheduler.scheduled_job('cron', day='*', hour='07', minute='30', second='0')
    #def rule_water_front_on(): do_job(water_front_on)

    #@scheduler.scheduled_job('cron', day='*', hour='07', minute='32', second='0')
    #def rule_water_front_off(): do_job(water_front_off)

    #@scheduler.scheduled_job('cron', day='*', hour='07', minute='33', second='0')
    #def rule_water_back_on(): do_job(water_back_on)

    #@scheduler.scheduled_job('cron', day='*', hour='07', minute='35', second='0')
    #def rule_water_back_off(): do_job(water_back_off)

    pass

except Exception, ex:
    Log.logger.error('Unable to initialise apscheduler based rules, err={}'.format(ex))

###### JOBS executed asyncronously via a thread pool ######
def test():
    Log.logger.info("Test rule")

def back_pump_on():
    Log.logger.info('back pump on')
    __update_custom_relay('back pump relay',1)
    #with app.test_request_context():
    #    Log.logger.info(redirect('/apiv1/relay/get'))
    # start the pump
    # open valve

def back_pump_off():
    Log.logger.info('back pump off')
    __update_custom_relay('back pump relay',0)


def water_front_on():
    Log.logger.info('water front on')
    back_pump_on()
    __update_custom_relay('front valve relay',1)


def water_front_off():
    Log.logger.info('water front off')
    __update_custom_relay('front valve relay',0)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()

def water_back_on():
    Log.logger.info('water back on')
    back_pump_on()
    __update_custom_relay('back valve relay',1)


def water_back_off():
    Log.logger.info('water back off')
    __update_custom_relay('back valve relay',0)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()

def __update_custom_relay(relay_pin_name, power_is_on):
    with app.test_client() as c:
        msg = c.get('/apiv1/db_update/model_name=ZoneCustomRelay&'
                'filter_name=relay_pin_name&filter_value={}&field_name=relay_is_on&field_value={}'.
                format(relay_pin_name, power_is_on)).data
    Log.logger.info(msg)