import time
from main.logger_helper import Log
from main import app
from main.admin import models

try:
    # sometimes I get "ImportError: cannot import name scheduler" so trying two import methods
    from rule import scheduler
except Exception:
    from . import scheduler

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

# two types of rules are supported:
# 1: cron based rules
# https://apscheduler.readthedocs.org/en/latest/userguide.html#adding-jobs
# https://apscheduler.readthedocs.org/en/v2.1.2/cronschedule.html
# 2: value changed rules, first obj parameter is mandatory. function will execute for object changed
# that have type=obj


# ###### VALUE TRIGGER RULES ########
# first parameter must have an object type equal to the object for which you get events in case there are DB changes
# 2nd parameter will contain list of fields changed

def execute_macro(obj=models.Rule(), field_changed_list=None):
    if obj.execute_now:
        obj.execute_now = False
    return 'rule execute macro ok'


def rule_node(obj=models.Node(), field_changed_list=None):
    if not field_changed_list:
        field_changed_list = []
    return 'rule node ok'


# min & max temperatures
def rule_sensor_temp_target(obj=models.Sensor(), field_changed_list=None):
    if not field_changed_list:
        field_changed_list = []
    temp = obj.temperature
    return 'rule temp ok'


# VALUE TRIGGER RULES END ###########


# ##### JOBS are executed asyncronously via a thread pool ######


# ## MACROS - must not have any parameter and must not start with "_" to exec as API and show in WEB UI#####

def test():
    Log.logger.info("Test rule")


def toggle_gate():
    Log.logger.info('Rule: toggle gate')
    __update_custom_relay('gate relay', 1)
    time.sleep(0.5)
    __update_custom_relay('gate relay', 0)


def back_pump_on():
    Log.logger.info('Rule: back pump on')
    __update_custom_relay('back pump relay', 1)
    # with app.test_request_context():
    #    Log.logger.info(redirect('/apiv1/relay/get'))
    # start the pump
    # open valve


def back_pump_off():
    Log.logger.info('back pump off')
    __update_custom_relay('back pump relay pi', 0)


def water_front_on():
    Log.logger.info('water front on')
    back_pump_on()
    __update_custom_relay('front valve relay pi', 1)


def water_front_off():
    Log.logger.info('water front off')
    __update_custom_relay('front valve relay pi', 0)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()


def water_back_on():
    Log.logger.info('water back on')
    back_pump_on()
    __update_custom_relay('back valve relay pi', 1)


def water_back_off():
    Log.logger.info('water back off')
    __update_custom_relay('back valve relay pi', 0)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()

# ##### MACROS END ##############


# ###### UTILITIES - start with "__" ##########


def __update_custom_relay(relay_pin_name, power_is_on):
    with app.test_client() as c:
        msg = c.get('/apiv1/db_update/model_name=ZoneCustomRelay&'
                    'filter_name=relay_pin_name&filter_value={}&field_name=relay_is_on&field_value={}'.
                    format(relay_pin_name, power_is_on)).data
    Log.logger.info(msg)
