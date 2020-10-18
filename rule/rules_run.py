import time
import sys
import threading
import datetime
from main.logger_helper import L
from main import sqlitedb
from storage.model import m
from rule import rule_common

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    last_bell = datetime.datetime.min
    has_zwave = False

    def __init__(self):
        pass


try:
    from sensor import zwave
    P.has_zwave = True
except ImportError as ie:
    L.l.info("Zwave module cannot be imported")

try:
    # sometimes I get "ImportError: cannot import name scheduler" so trying two import methods
    from rule import scheduler
except ImportError:
    from . import scheduler


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

def execute_macro(obj=m.Rule(), change=None, force_exec=False):
    if obj.execute_now or force_exec:
        L.l.info('Execute macro {} as execute_now is True'.format(obj.command))
        # obj.execute_now = False
        # obj.commit_record_to_db()
        func = getattr(sys.modules[__name__], obj.command)
        if obj.is_async:
            threading.Thread(target=func).start()
            # thread.start_new_thread(func, ())
            result = "rule started async"
        else:
            result = func()
    else:
        L.l.info('Ignoring execute macro as execute_now is False')
        result = "Rule not executed as execute_now is False"
    return result


def rule_node(obj=m.Node(), change=None):
    if not change:
        field_changed_list = []
    return 'rule node ok'


def rule_alarm(obj=m.ZoneAlarm(), change=None):
    if obj.alarm_pin_triggered:
        if obj.start_alarm:
            L.l.debug('Rule Alarm ON:  pin={} triggered={}'.format(obj.alarm_pin_name, obj.alarm_pin_triggered))
            msg = 'Alarm ON {}'.format(obj.alarm_pin_name)
            rule_common.notify_via_all(title=msg, message=msg, priority=3)
        if obj.alarm_pin_name == 'sonerie':
            if (datetime.datetime.now() - P.last_bell).total_seconds() > 5:
                threading.Thread(target=rule_common.play_bell_local,args=('SonnetteBasse.wav', )).start()
                # thread.start_new_thread(rule_common.play_bell_local, ('SonnetteBasse.wav', ))
                rule_common.notify_via_all(title="Sonerie", message="Sonerie", priority=1)
                P.last_bell = datetime.datetime.now()
                # rule_common.send_notification(title="Sonerie", priority=2)
                # rule_common.send_chat(message="Sonerie", notify=True)
        # elif obj.alarm_pin_name == 'usa intrare':
        #     thread.start_new_thread(rule_common.play_bell_local, ('warning.wav',))
        elif obj.alarm_pin_name == 'poarta':
            pass
            # thread.start_new_thread(rule_common.play_bell_local, ('121798__boss-music__bird.wav',))
            # rule_common.send_notification(title="Gate Open", priority=2)
            # rule_common.send_chat(message="Gate Open", notify=True)
        elif obj.alarm_pin_name == 'portita':
            # thread.start_new_thread(rule_common.play_bell_local, ('121798__boss-music__bird.wav',))
            threading.Thread(target=rule_common.play_bell_local, args=('121798__boss-music__bird.wav',)).start()
            rule_common.send_notification(title="Portita Open", priority=2)
            rule_common.send_chat(message="Portita Open", notify=True)
        elif obj.alarm_pin_name == 'car vibrate':
            msg = "Car Vibration"
            # rule_common.notify_via_all(title=msg, message=msg, priority=3)
        # elif obj.alarm_pin_name == 'birou':
        #    thread.start_new_thread(rule_common.play_bell_local, ('29621__infobandit__phone.wav',))
    # else:
    #    Log.logger.info('Rule Alarm OFF: pin={} triggered={}'.format(obj.alarm_pin_name, obj.alarm_pin_triggered))
    else:
        if obj.alarm_pin_name == 'poarta':
            pass
            # rule_common.send_notification(title="Gate Closed", priority=2)
            # rule_common.send_chat(message="Gate Closed", notify=True)
        elif obj.alarm_pin_name == 'portita':
            rule_common.send_notification(title="Portita Closed", priority=2)
            rule_common.send_chat(message="Portita Closed", notify=True)
    return 'zone alarm ok'


# min & max temperatures
def rule_sensor_temp_target(obj=m.Sensor(), change=None):
    if not change:
        field_changed_list = []
    #temp = obj.temperature
    return 'rule temp ok'


class TempStore:
    max_temp = {'indoor':           {'air': 35, 'water': 85, 'glicol': 90},
                'indoor_heated':    {'air': 35, 'water': 85, 'glicol': 90},
                'outdoor':          {'air': 39, 'water': 85, 'glicol': 90},
                'outdoor_heated':   {'air': 95, 'water': 85, 'glicol': 90}}
    min_temp = {'indoor':           {'air': 5, 'water': 5, 'glicol': 5},
                'indoor_heated':    {'air': 15, 'water': 5, 'glicol': 5},
                'outdoor':          {'air': -15, 'water': 1, 'glicol': 1},
                'outdoor_heated':   {'air': -15, 'water': 1, 'glicol': 1}}
    temp_last = {} # {name, []}


# catch sudden changes or extremes (fire or cold)
def rule_sensor_temp_extreme(obj=m.Sensor(), change=None):
    if hasattr(obj, 'temperature') and obj.temperature is not None:
        if sqlitedb:
            # m = ZoneSensor()
            zonesensor = m().query_filter_first(m.sensor_name == obj.sensor_name)
        else:
            zonesensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_name: obj.sensor_name})
        if zonesensor is not None and zonesensor.target_material is not None:
            if sqlitedb:
                # m = m.Zone
                zone = m().query_filter_first(m.id == zonesensor.zone_id)
            else:
                zone = m.Zone.find_one({m.Zone.id: zonesensor.zone_id})
            if zone is not None:
                max = min = None
                if zone.is_indoor:
                    location = 'indoor'
                elif zone.is_indoor_heated:
                    location = 'indoor_heated'
                elif zone.is_outdoor:
                    location = 'outdoor'
                elif zone.is_outdoor_heated:
                    location = 'outdoor_heated'
                else:
                    L.l.warning("Zone {} has no indoor/outdoor location set".format(zone.name))
                    return False

                max_temp = TempStore.max_temp[location]
                if zonesensor.target_material in max_temp:
                    max = max_temp[zonesensor.target_material]
                else:
                    L.l.warning("Unknown max target material {}".format(zonesensor.target_material))
                min_temp = TempStore.min_temp[location]
                if zonesensor.target_material in min_temp:
                    min = min_temp[zonesensor.target_material]
                else:
                    L.l.warning("Unknown min target material {}".format(zonesensor.target_material))

                if max is not None and obj.temperature >= max:
                    rule_common.notify_via_all(title="Max temperature reached for {} is {}".format(
                        obj.sensor_name, obj.temperature), message="!", priority=1)
                if min is not None and obj.temperature <= min:
                    rule_common.notify_via_all(title="Min temperature reached for {} is {}".format(
                        obj.sensor_name, obj.temperature), message="!", priority=1)
            else:
                L.l.warning("Cannot find a zone for zone_sensor {}".format(zonesensor))
    return True


# ups rule
def rule_ups_power(obj=m.Ups(), change=None):
    # Log.logger.info("changed list is {}".format(field_changed_list))
    if change is not None:
        if 'power_failed' in change:
            if obj.power_failed:
                rule_common.notify_via_all(title="UPS power LOST", message="power lost", priority=1)
            else:
                rule_common.notify_via_all(title="UPS power OK", message="power is back", priority=1)
        if 'battery_voltage' in change:
            if obj.battery_voltage <= 52:
                rule_common.notify_via_all("UPS battery low at {} volts".format(obj.battery_voltage), "Low voltage")
        if 'load_percent' in change:
            if obj.load_percent >= 60:
                rule_common.notify_via_all("UPS load HIGH at {}".format(obj.load_percent), "High ups load")
        if 'input_voltage' in change:
            if obj.input_voltage <= 190:
                rule_common.send_notification(title="Low grid voltage {}".format(obj.input_voltage),
                                              message="Grid low at {} volts".format(obj.input_voltage))
    return 'ups rule ok'


# VALUE TRIGGER RULES END ###########

# ##### JOBS are executed asyncronously via a thread pool ######

# ## MACROS - must not have any parameter and must not start with "_" to exec as API and show in WEB UI#####
# year=*;month=*;week=*;day=*;day_of_week=*;hour=*;minute=*;second=0;is_active=true
def test_code():
    """second=18;is_active=false"""
    L.l.info("Test rule code 3")
    #rule_common.update_custom_relay('test_relay', True)
    #time.sleep(0.5)
    #rule_common.update_custom_relay('test_relay', False)
    # rule_common.send_notification(title='Alarm ON {}'.format('test 1'), priority=3)
    # rule_common.send_notification(title='Alarm ON {}'.format('test 2'), priority=3)
    # rule_common.send_notification(title='Alarm ON {}'.format('test 3'), priority=3)
    pass


def toggle_gate():
    L.l.info('Rule: toggle gate relay on {}'.format(datetime.datetime.now()))
    rule_common.update_custom_relay('gate_relay', True)
    time.sleep(1)
    L.l.info('Rule: toggle gate relay off{}'.format(datetime.datetime.now()))
    rule_common.update_custom_relay('gate_relay', False)


def morning_alarm_dormitor():
    """day_of_week=1-5;hour=7;minute=15;is_active=true"""
    L.l.info('Rule: morning alarm dormitor')
    # execfile("~/PYC/scripts/audio/mpc-play.sh 6603 music")
    exec(open("~/PYC/scripts/audio/mpc-play.sh 6603 music").read())


def water_all_3_minute():
    """is_async=true"""
    water_front_3_minute()
    water_back_3_minute()


def water_main_all_3_minute():
    """is_async=true"""
    water_front_main_3_minute()
    water_back_main_3_minute()


def water_front_3_minute():
    """is_async=true"""
    water_front_on()
    time.sleep(60*3)
    water_front_off()


def water_back_3_minute():
    """is_async=true"""
    water_back_on()
    time.sleep(60*3)
    water_back_off()


def water_front_main_3_minute():
    """is_async=true"""
    water_front_main_on()
    time.sleep(60*3)
    water_front_main_off()


def water_back_main_3_minute():
    """is_async=true"""
    water_back_main_on()
    time.sleep(60*3)
    water_back_main_off()


def back_pump_on():
    """month=05-09;hour=07;minute=50;is_active=false"""
    L.l.info('Rule: back pump on')
    rule_common.update_custom_relay('back_pump_relay', True)
    # with app.test_request_context():
    #    Log.logger.info(redirect('/apiv1/relay/get'))
    # start the pump
    # open valve


def back_pump_off():
    """month=05-09;hour=07;minute=56;is_active=false"""
    L.l.info('back pump off')
    rule_common.update_custom_relay('back_pump_relay', False)


def water_front_on():
    """month=05-09;hour=07;minute=50;is_active=false"""
    L.l.info('water front on')
    back_pump_on()
    rule_common.update_custom_relay('front_valve_relay', True)


def water_front_off():
    """month=05-09;hour=07;minute=52;is_active=false"""
    L.l.info('water front off')
    rule_common.update_custom_relay('front_valve_relay', False)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()


def water_front_main_on():
    """month=05-09;hour=07;minute=50;is_active=false"""
    L.l.info('water front main on')
    rule_common.update_custom_relay('front_main_valve_relay', True)
    rule_common.update_custom_relay('front_valve_relay', True)


def water_front_main_off():
    """month=05-09;hour=07;minute=52;is_active=false"""
    L.l.info('water front main off')
    rule_common.update_custom_relay('front_main_valve_relay', False)
    rule_common.update_custom_relay('front_valve_relay', True)


def water_back_on():
    """month=05-09;hour=07;minute=54;is_active=false"""
    L.l.info('water back on')
    back_pump_on()
    rule_common.update_custom_relay('back_valve_relay', True)


def water_back_off():
    """month=05-09;hour=07;minute=57;is_active=false"""
    L.l.info('water back off')
    rule_common.update_custom_relay('back_valve_relay', False)
    # let the pump build some pressure
    time.sleep(5)
    # pump off if no other zone is on?
    back_pump_off()


def water_back_main_on():
    """month=05-09;hour=07;minute=54;is_active=false"""
    L.l.info('water back main on')
    rule_common.update_custom_relay('front_main_valve_relay', True)
    rule_common.update_custom_relay('back_valve_relay', True)


def water_back_main_off():
    """month=05-09;hour=07;minute=57;is_active=false"""
    L.l.info('water back main off')
    rule_common.update_custom_relay('front_main_valve_relay', False)
    rule_common.update_custom_relay('back_valve_relay', False)



def front_lights_on():
    rule_common.update_custom_relay('front_lights_relay', True)


def zwave_start_inclusion():
    if P.has_zwave:
        zwave.include_node()


def zwave_stop_inclusion():
    if P.has_zwave:
        zwave.stop_include_node()

# ##### MACROS END ##############

