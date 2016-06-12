import time
import sys
from main.logger_helper import Log
from main import app
from main.admin import models
from webui.api import api_v1

try:
    # sometimes I get "ImportError: cannot import name scheduler" so trying two import methods
    from rule import scheduler
except ImportError:
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
        Log.logger.info('Execute macro {} as execute_now is True'.format(obj.command))
        # obj.execute_now = False
        # obj.commit_record_to_db()
        result = getattr(sys.modules[__name__], obj.command)()
    else:
        Log.logger.info('Ignoring execute macro as execute_now is False')
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

def test_code():
    Log.logger.info("Test rule code")
    __update_custom_relay('test_relay', True)
    time.sleep(0.3)
    __update_custom_relay('test_relay', False)


def toggle_gate():
    Log.logger.info('Rule: toggle gate')
    __update_custom_relay('gate_relay', True)
    time.sleep(0.3)
    __update_custom_relay('gate_relay', False)


def back_pump_on():
    Log.logger.info('Rule: back pump on')
    __update_custom_relay('back pump relay', True)
    # with app.test_request_context():
    #    Log.logger.info(redirect('/apiv1/relay/get'))
    # start the pump
    # open valve


def back_pump_off():
    Log.logger.info('back pump off')
    __update_custom_relay('back pump relay pi', False)


def water_front_on():
    Log.logger.info('water front on')
    back_pump_on()
    __update_custom_relay('front valve relay pi', True)


def water_front_off():
    Log.logger.info('water front off')
    __update_custom_relay('front valve relay pi', False)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()


def water_back_on():
    Log.logger.info('water back on')
    back_pump_on()
    __update_custom_relay('back valve relay pi', True)


def water_back_off():
    Log.logger.info('water back off')
    __update_custom_relay('back valve relay pi', False)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()

# ##### MACROS END ##############


# ###### UTILITIES - start with "__" ##########

# carefull with API fields order to match app.route definition
def __update_custom_relay(relay_pin_name, power_is_on):
    # with app.test_client() as c:
    msg = api_v1.generic_db_update(model_name="ZoneCustomRelay", filter_name="relay_pin_name",
                                   field_name="relay_is_on", filter_value=relay_pin_name, field_value=power_is_on)
        # msg = c.get('/apiv1/db_update/model_name=ZoneCustomRelay&'
        #            'filter_name=relay_pin_name&field_name=relay_is_on&filter_value={}&field_value={}'.
        #            format(relay_pin_name, power_is_on)).data
    Log.logger.info(msg)
