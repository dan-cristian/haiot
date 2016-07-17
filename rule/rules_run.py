import time
import sys
import thread
import datetime
from main.logger_helper import Log
from main.admin import models
import rule_common

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
# http://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html?highlight=day_of_week
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
        function = getattr(sys.modules[__name__], obj.command)
        if obj.is_async:
            thread.start_new_thread(function, ())
            result = "rule started async"
        else:
            result = function()
    else:
        Log.logger.info('Ignoring execute macro as execute_now is False')
        result = "Rule not executed as execute_now is False"
    return result


def rule_node(obj=models.Node(), field_changed_list=None):
    if not field_changed_list:
        field_changed_list = []
    return 'rule node ok'


def rule_alarm(obj=models.ZoneAlarm(), field_changed_list=None):
    # Log.logger.info('Rule Alarm: obj={} fields={}'.format(obj, field_changed_list))
    if obj.alarm_status == 1:
        Log.logger.info('Rule Alarm ON:  pin={} status={}'.format(obj.alarm_pin_name, obj.alarm_status))
        rule_common.send_notification(title="Alarm ON %s" % obj.alarm_pin_name)
        if obj.alarm_pin_name == 'sonerie':
            thread.start_new_thread(rule_common.play_bell_local, ('british.wav', ))
        elif obj.alarm_pin_name == 'usa intrare':
            thread.start_new_thread(rule_common.play_bell_local, ('warning.wav',))
        elif obj.alarm_pin_name == 'poarta':
            thread.start_new_thread(rule_common.play_bell_local, ('weatherwarning.wav',))
        elif obj.alarm_pin_name == 'portita':
            thread.start_new_thread(rule_common.play_bell_local, ('boat_hor.wav',))
        elif obj.alarm_pin_name == 'birou':
            thread.start_new_thread(rule_common.play_bell_local, ('29621__infobandit__phone.wav',))
    else:
        Log.logger.info('Rule Alarm OFF: pin={} status={}'.format(obj.alarm_pin_name, obj.alarm_status))
    return 'zone alarm ok'


# min & max temperatures
def rule_sensor_temp_target(obj=models.Sensor(), field_changed_list=None):
    if not field_changed_list:
        field_changed_list = []
    temp = obj.temperature
    return 'rule temp ok'


# VALUE TRIGGER RULES END ###########


# ##### JOBS are executed asyncronously via a thread pool ######


# ## MACROS - must not have any parameter and must not start with "_" to exec as API and show in WEB UI#####
# year=*;month=*;week=*;day=*;day_of_week=*;hour=*;minute=*;second=0;is_active=1

def test_code():
    """second=18;is_active=0"""
    Log.logger.info("Test rule code 3")
    rule_common.update_custom_relay('test_relay', True)
    time.sleep(0.5)
    rule_common.update_custom_relay('test_relay', False)


def toggle_gate():
    Log.logger.info('Rule: toggle gate relay on {}'.format(datetime.datetime.now()))
    rule_common.update_custom_relay('gate_relay', True)
    time.sleep(1)
    Log.logger.info('Rule: toggle gate relay off{}'.format(datetime.datetime.now()))
    rule_common.update_custom_relay('gate_relay', False)


def morning_alarm_dormitor():
    """day_of_week=1-5;hour=7;minute=15;is_active=1"""
    Log.logger.info('Rule: morning alarm dormitor')
    execfile("~/PYC/scripts/audio/mpc-play.sh 6603 music")


def water_all_3_minute():
    """is_async=1"""
    water_front_3_minute()
    water_back_3_minute()


def water_main_all_3_minute():
    """is_async=1"""
    water_front_main_3_minute()
    water_back_main_3_minute()


def water_front_3_minute():
    """is_async=1"""
    water_front_on()
    time.sleep(60*3)
    water_front_off()


def water_back_3_minute():
    """is_async=1"""
    water_back_on()
    time.sleep(60*3)
    water_back_off()


def water_front_main_3_minute():
    """is_async=1"""
    water_front_main_on()
    time.sleep(60*3)
    water_front_main_off()


def water_back_main_3_minute():
    """is_async=1"""
    water_back_main_on()
    time.sleep(60*3)
    water_back_main_off()


def back_pump_on():
    """month=05-09;hour=07;minute=50;is_active=0"""
    Log.logger.info('Rule: back pump on')
    rule_common.update_custom_relay('back_pump_relay', True)
    # with app.test_request_context():
    #    Log.logger.info(redirect('/apiv1/relay/get'))
    # start the pump
    # open valve


def back_pump_off():
    """month=05-09;hour=07;minute=56;is_active=0"""
    Log.logger.info('back pump off')
    rule_common.update_custom_relay('back_pump_relay', False)


def water_front_on():
    """month=05-09;hour=07;minute=50;is_active=0"""
    Log.logger.info('water front on')
    back_pump_on()
    rule_common.update_custom_relay('front_valve_relay', True)


def water_front_off():
    """month=05-09;hour=07;minute=52;is_active=0"""
    Log.logger.info('water front off')
    rule_common.update_custom_relay('front_valve_relay', False)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()


def water_front_main_on():
    """month=05-09;hour=07;minute=50;is_active=0"""
    Log.logger.info('water front main on')
    rule_common.update_custom_relay('front_main_valve_relay', True)
    rule_common.update_custom_relay('front_valve_relay', True)


def water_front_main_off():
    """month=05-09;hour=07;minute=52;is_active=0"""
    Log.logger.info('water front main off')
    rule_common.update_custom_relay('front_main_valve_relay', False)
    rule_common.update_custom_relay('front_valve_relay', True)


def water_back_on():
    """month=05-09;hour=07;minute=54;is_active=0"""
    Log.logger.info('water back on')
    back_pump_on()
    rule_common.update_custom_relay('back_valve_relay', True)


def water_back_off():
    """month=05-09;hour=07;minute=57;is_active=0"""
    Log.logger.info('water back off')
    rule_common.update_custom_relay('back_valve_relay', False)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()


def water_back_main_on():
    """month=05-09;hour=07;minute=54;is_active=0"""
    Log.logger.info('water back main on')
    rule_common.update_custom_relay('front_main_valve_relay', True)
    rule_common.update_custom_relay('back_valve_relay', True)


def water_back_main_off():
    """month=05-09;hour=07;minute=57;is_active=0"""
    Log.logger.info('water back main off')
    rule_common.update_custom_relay('front_main_valve_relay', False)
    rule_common.update_custom_relay('back_valve_relay', False)


def main_heat_on():
    rule_common.update_command_override_relay('main_heat_relay')

# ##### MACROS END ##############

